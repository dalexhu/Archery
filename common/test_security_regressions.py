"""Exercise the high-priority CodeQL findings with synthetic data and mocks."""

import json
import logging
import subprocess
import sys
import textwrap
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from django.test import RequestFactory

from common.utils import ding_api, sendmsg, wx_api
from sql import instance, views
from sql.engines.doris import DorisEngine
from sql.engines.goinception import GoInceptionEngine
from sql.engines.mongo import MongoEngine
from sql.engines.mysql import MysqlEngine, MysqlForkType
from sql.plugins.plugin import Plugin


@pytest.mark.parametrize("prefix", ["db.", "db.getCollection('"])
def test_mongo_rejects_long_malformed_query_without_backtracking(prefix):
    code = textwrap.dedent("""
        import os, sys
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'archery.settings')
        import django
        django.setup()
        from sql.engines.mongo import MongoEngine
        engine = MongoEngine()
        engine.get_all_tables = lambda *a, **kw: (_ for _ in ()).throw(
            AssertionError('Malformed query must not access an engine')
        )
        assert engine.query_check(sql=sys.argv[1])['bad_query']
    """)
    result = subprocess.run(
        [sys.executable, "-c", code, prefix + "0" * 80 + "!"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("collection", ["items", "a.b", "集合"])
def test_mongo_valid_collection_query_is_preserved(collection):
    engine = MongoEngine()
    engine.get_all_tables = Mock(return_value=SimpleNamespace(rows=[collection]))
    result = engine.query_check(db_name="test", sql=f"db.{collection}.find({{}})")
    assert not result["bad_query"]


@pytest.mark.parametrize("field", ["db_name", "target_db_name"])
@pytest.mark.parametrize("value", ["../../escaped", "..\\escaped", "bad\x00name"])
def test_schemasync_rejects_path_input_before_lookup_or_command(
    mocker, settings, tmp_path, field, value
):
    settings.BASE_DIR = str(tmp_path)
    lookup = mocker.patch("sql.instance.Instance.objects.get")
    sync = mocker.patch("sql.instance.SchemaSync")
    request = RequestFactory().post(
        "/instance/schemasync/",
        {
            "instance_name": "source",
            "target_instance_name": "target",
            "db_name": "app",
            "target_db_name": "app",
            field: value,
        },
    )
    request.user = SimpleNamespace(has_perms=lambda permissions: True)
    response = instance.schemasync(request)
    assert response.status_code == 400
    assert json.loads(response.content)["status"] == 1
    lookup.assert_not_called()
    sync.assert_not_called()


def test_rollback_uses_canonical_database_id_for_filename(mocker, settings, tmp_path):
    settings.BASE_DIR = str(tmp_path)
    mocker.patch("sql.views.can_rollback", return_value=True)
    mocker.patch(
        "sql.views.SqlWorkflow.objects.get",
        return_value=SimpleNamespace(id=1, instance=None),
    )
    engine = mocker.patch("sql.views.get_engine").return_value
    engine.get_rollback.return_value = [(1, "synthetic rollback")]
    request = RequestFactory().get(
        "/rollback/", {"workflow_id": "+0001", "download": "1"}
    )
    request.user = SimpleNamespace()
    response = views.rollback(request)
    try:
        assert b"synthetic rollback" in b"".join(response.streaming_content)
        assert (tmp_path / "downloads/rollback/rollback_1.sql").is_file()
        assert response["Content-Disposition"].endswith('"rollback_1.sql"')
    finally:
        response.close()


@pytest.mark.parametrize("engine_type", [MysqlEngine, DorisEngine])
def test_sql_failure_logs_do_not_include_sql_or_exception_secrets(
    mocker, caplog, engine_type
):
    engine = engine_type()
    cursor = mocker.patch.object(
        engine, "get_connection"
    ).return_value.cursor.return_value
    cursor.execute.side_effect = RuntimeError("secret-in-error-test-only")
    with caplog.at_level(logging.DEBUG, logger="default"):
        result = engine.execute(
            sql="CREATE USER x IDENTIFIED BY 'secret-in-sql-test-only'",
            close_conn=False,
        )
    assert result.error == "secret-in-error-test-only"
    assert "secret-in-sql-test-only" not in caplog.text
    assert "secret-in-error-test-only" not in caplog.text
    assert "RuntimeError" in caplog.text


@pytest.mark.parametrize("provider", [ding_api, wx_api])
def test_token_failure_does_not_log_response_secrets(mocker, caplog, provider):
    mocker.patch.object(provider, "SysConfig").return_value.get.return_value = (
        "secret-in-config-test-only"
    )
    mocker.patch.object(provider.requests, "get").return_value.json.return_value = {
        "errcode": 40013,
        "errmsg": "secret-in-response-test-only",
    }
    if provider is ding_api:
        mocker.patch.object(provider, "rs").execute_command.return_value = None
        function = provider.get_access_token
    else:
        mocker.patch.object(provider, "cache").get.return_value = None
        function = provider.get_wx_access_token
    with caplog.at_level(logging.DEBUG, logger="default"):
        assert function() is None
    assert "secret-in-" not in caplog.text
    assert caplog.records


@pytest.mark.parametrize("method", ["send_ding2user", "send_wx2user"])
def test_message_failure_does_not_log_token_or_message(mocker, caplog, method):
    mocker.patch.object(
        sendmsg, "get_access_token", return_value="secret-token-test-only"
    )
    mocker.patch.object(
        sendmsg, "get_wx_access_token", return_value="secret-token-test-only"
    )
    mocker.patch.object(sendmsg.requests, "post").return_value.json.return_value = {
        "errcode": 1,
        "errmsg": "secret-response-test-only",
    }
    sender = object.__new__(sendmsg.MsgSender)
    sender.ding_agent_id = sender.wx_agent_id = "test-only"
    with caplog.at_level(logging.DEBUG, logger="default"):
        if method == "send_ding2user":
            sender.send_ding2user(["test-user"], "secret-message-test-only")
        else:
            sender.send_wx2user("secret-message-test-only", ["test-user"])
    assert "secret-" not in caplog.text
    assert caplog.records


def test_plugin_keeps_shell_metacharacters_in_a_single_argument(mocker):
    popen = mocker.patch("sql.plugins.plugin.subprocess.Popen")
    plugin = Plugin("/test-only/tool")
    payload = "x; $(touch /test-only/canary) --other-option"
    args = plugin.generate_args2cmd({"query": payload})
    plugin.execute_cmd(args)
    assert popen.call_args.args[0] == ["/test-only/tool", "-query", payload]
    assert popen.call_args.kwargs["shell"] is False


@pytest.mark.parametrize("engine_type", [MysqlEngine, GoInceptionEngine])
def test_query_engine_preserves_intended_sql(mocker, engine_type):
    engine = engine_type()
    if engine_type is MysqlEngine:
        engine._server_fork_type = MysqlForkType.MYSQL
    cursor = mocker.patch.object(
        engine, "get_connection"
    ).return_value.cursor.return_value
    cursor.description = []
    sql = "SELECT 'synthetic literal'"
    engine.query(sql=sql, close_conn=False)
    assert cursor.execute.call_args.args[0] == sql


def test_schemasync_cannot_read_a_matching_file_outside_output_directory(
    mocker, settings, tmp_path
):
    root = tmp_path / "app"
    root.mkdir()
    settings.BASE_DIR = str(root)
    canary = root / "escaped_123.20000101.patch.sql"
    canary.write_text("synthetic-private-canary")
    fake_instance = SimpleNamespace(
        host="test-only",
        port=3306,
        get_username_password=lambda: ("test-only", "test-only"),
    )
    mocker.patch("sql.instance.Instance.objects.get", return_value=fake_instance)
    mocker.patch(
        "sql.instance.time",
        SimpleNamespace(
            time=lambda: 123, localtime=lambda: None, strftime=lambda *args: "20000101"
        ),
    )
    sync = mocker.patch("sql.instance.SchemaSync").return_value
    sync.check_args.return_value = {"status": 0}
    sync.generate_args2cmd.return_value = ["test-only"]
    sync.execute_cmd.return_value.communicate.return_value = ("", "")
    request = RequestFactory().post(
        "/instance/schemasync/",
        {
            "instance_name": "source",
            "target_instance_name": "target",
            "db_name": "app",
            "target_db_name": "../../escaped",
        },
    )
    request.user = SimpleNamespace(has_perms=lambda permissions: True)
    response = instance.schemasync(request)
    assert b"synthetic-private-canary" not in response.content
    assert response.status_code == 400
    sync.execute_cmd.assert_not_called()


@pytest.mark.parametrize("success", [False, True])
@pytest.mark.parametrize(
    "method", ["send_ding", "send_qywx_webhook", "send_feishu_webhook"]
)
def test_webhook_logs_do_not_include_url_credentials_or_payload(
    mocker, caplog, method, success
):
    response = {"errcode": 0 if success else 1, "errmsg": "secret-response-test-only"}
    if method == "send_feishu_webhook":
        response = {"code": 0 if success else 1, "message": "secret-response-test-only"}
    mocker.patch.object(sendmsg.requests, "post").return_value.json.return_value = (
        response
    )
    url = "https://test.invalid/v2/hook?access_token=secret-url-test-only"
    sender = object.__new__(sendmsg.MsgSender)
    with caplog.at_level(logging.DEBUG, logger="default"):
        if method == "send_feishu_webhook":
            sender.send_feishu_webhook(url, "test title", "secret-content-test-only")
        elif method == "send_ding":
            sender.send_ding(url, "secret-content-test-only")
        else:
            sender.send_qywx_webhook(url, "secret-content-test-only")
    assert "secret-" not in caplog.text
    assert caplog.records


@pytest.mark.parametrize("workflow_id", ["../../escaped", "1/../escaped"])
def test_rollback_rejects_non_integer_id_before_any_file_access(mocker, workflow_id):
    mocker.patch("sql.views.can_rollback", return_value=True)
    lookup = mocker.patch("sql.views.SqlWorkflow.objects.get")
    file_open = mocker.patch("sql.views.open", create=True)
    request = RequestFactory().get(
        "/rollback/", {"workflow_id": workflow_id, "download": "1"}
    )
    request.user = SimpleNamespace()
    with pytest.raises(ValueError):
        views.rollback(request)
    lookup.assert_not_called()
    file_open.assert_not_called()


def test_cloud_authentication_failure_does_not_expose_exception(mocker):
    from common.utils.aliyun_sdk import Aliyun

    mocker.patch(
        "common.utils.aliyun_sdk.AcsClient", side_effect=RuntimeError("secret-canary")
    )
    rds = SimpleNamespace(
        rds_dbinstanceid="test",
        ak=SimpleNamespace(raw_key_id="id", raw_key_secret="secret"),
    )
    with pytest.raises(RuntimeError, match="^Cloud authentication failed$") as error:
        Aliyun(rds)
    assert error.value.__suppress_context__


def test_email_failure_does_not_return_traceback_or_secret(mocker, caplog):
    sender = sendmsg.MsgSender(
        server="invalid", user="test@example.invalid", password="secret"
    )
    mocker.patch(
        "common.utils.sendmsg.smtplib.SMTP", side_effect=RuntimeError("secret-canary")
    )
    with caplog.at_level(logging.ERROR):
        result = sender.send_email("test", "synthetic", ["recipient@example.invalid"])
    assert result == "Email delivery failed"
    assert "secret-canary" not in caplog.text
    assert "Traceback" not in result


@pytest.mark.parametrize("operation", ["resources", "description"])
def test_resource_service_hides_unexpected_engine_errors(mocker, operation):
    from sql.services import resource_service

    mocker.patch.object(
        resource_service, "_resolve_instance_for_user", return_value=Mock()
    )
    mocker.patch.object(
        resource_service,
        "get_engine",
        side_effect=RuntimeError("/private/secret-canary"),
    )
    if operation == "resources":
        result = resource_service.list_instance_resources(
            Mock(), "database", instance_name="test"
        )
    else:
        result = resource_service.describe_table_structure(
            Mock(), "test", "db", "table"
        )
    assert result["status"] == 1
    assert "secret-canary" not in json.dumps(result)
    assert "Operation failed" in result["msg"]


@pytest.mark.parametrize(
    "module_name,class_name",
    [("common.twofa.sms", "SMS"), ("common.twofa.totp", "TOTP")],
)
def test_two_factor_save_failure_hides_exception(mocker, module_name, class_name):
    import importlib

    module = importlib.import_module(module_name)
    mocker.patch.object(
        module.transaction, "atomic", side_effect=RuntimeError("secret-canary")
    )
    authenticator = getattr(module, class_name)(user=Mock())
    result = authenticator.save("synthetic")
    assert result["status"] == 1
    assert "secret-canary" not in json.dumps(result)

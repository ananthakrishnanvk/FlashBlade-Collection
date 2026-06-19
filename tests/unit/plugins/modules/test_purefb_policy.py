# Copyright: (c) 2026, Everpure Ansible Team <pure-ansible-team@everpuredata.com>
# GNU General Public License v3.0+ (see COPYING.GPLv3 or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for purefb_policy module (NFS export policy rule handling)."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import sys
from unittest.mock import Mock, MagicMock

# Mock external dependencies before importing module
sys.modules["pypureclient"] = MagicMock()
sys.modules["pypureclient.flashblade"] = MagicMock()
sys.modules["urllib3"] = MagicMock()
sys.modules["distro"] = MagicMock()
sys.modules["grp"] = MagicMock()
sys.modules["fcntl"] = MagicMock()
sys.modules["pwd"] = MagicMock()
sys.modules["syslog"] = MagicMock()
mock_termios = MagicMock()
mock_termios.TCSAFLUSH = 2
sys.modules["termios"] = mock_termios
sys.modules["tty"] = MagicMock()

# Mock ansible_collections module structure
sys.modules["ansible_collections"] = MagicMock()
sys.modules["ansible_collections.purestorage"] = MagicMock()
sys.modules["ansible_collections.purestorage.flashblade"] = MagicMock()
sys.modules["ansible_collections.purestorage.flashblade.plugins"] = MagicMock()
sys.modules["ansible_collections.purestorage.flashblade.plugins.module_utils"] = (
    MagicMock()
)
sys.modules[
    "ansible_collections.purestorage.flashblade.plugins.module_utils.purefb"
] = MagicMock()
sys.modules[
    "ansible_collections.purestorage.flashblade.plugins.module_utils.common"
] = MagicMock()
sys.modules[
    "ansible_collections.purestorage.flashblade.plugins.module_utils.version"
] = MagicMock()

from plugins.modules.purefb_policy import update_nfs_policy


def _existing_rule(access="root-squash"):
    """Build a mock SDK NFS export policy rule for client 10.0.10.42."""
    rule = Mock()
    rule.access = access
    rule.anongid = "100021"
    rule.anonuid = "20000021"
    rule.atime = True
    rule.client = "10.0.10.42"
    rule.fileid_32bit = False
    rule.permission = "rw"
    rule.secure = False
    rule.security = ["krb5", "krb5i", "krb5p", "sys"]
    rule.index = 1
    return rule


def _module(access):
    """Build a mock AnsibleModule whose desired rule has the given access."""
    module = Mock()
    module.check_mode = False
    module.params = {
        "name": "project96_nfs_policy",
        "client": "10.0.10.42",
        "permission": "rw",
        "access": access,
        "anonuid": "20000021",
        "anongid": "100021",
        "fileid_32bit": False,
        "atime": True,
        "secure": False,
        "security": ["krb5", "krb5i", "krb5p", "sys"],
        "before_rule": None,
        "context": "",
        "enabled": True,
    }
    module.fail_json = Mock(side_effect=SystemExit("fail_json called"))
    module.exit_json = Mock()
    return module


def _blade(existing_rule):
    """Build a mock blade returning the given existing rule."""
    blade = Mock()
    blade.get_versions.return_value.items = []  # no context API version

    rules_resp = Mock()
    rules_resp.status_code = 200
    rules_resp.total_item_count = 1
    rules_resp.items = [existing_rule]
    blade.get_nfs_export_policies_rules.return_value = rules_resp

    ok = Mock()
    ok.status_code = 200
    blade.patch_nfs_export_policies_rules.return_value = ok

    policy = Mock()
    policy.enabled = True
    policy_resp = Mock()
    policy_resp.items = [policy]
    blade.get_nfs_export_policies.return_value = policy_resp
    return blade


class TestUpdateNfsPolicyRule:
    """Regression tests for NFS export policy rule idempotency."""

    def test_access_change_triggers_patch(self):
        """Changing only access (root-squash -> no-squash) must PATCH the rule."""
        module = _module(access="no-squash")
        blade = _blade(_existing_rule(access="root-squash"))

        update_nfs_policy(module, blade)

        blade.patch_nfs_export_policies_rules.assert_called_once()
        # rule name targeted is "<policy>.<index>"
        call_kwargs = blade.patch_nfs_export_policies_rules.call_args[1]
        assert call_kwargs["names"] == ["project96_nfs_policy.1"]
        module.exit_json.assert_called_once_with(changed=True)

    def test_no_change_is_idempotent(self):
        """Identical desired state (incl. access) must not PATCH the rule."""
        module = _module(access="root-squash")
        blade = _blade(_existing_rule(access="root-squash"))

        update_nfs_policy(module, blade)

        blade.patch_nfs_export_policies_rules.assert_not_called()
        module.exit_json.assert_called_once_with(changed=False)

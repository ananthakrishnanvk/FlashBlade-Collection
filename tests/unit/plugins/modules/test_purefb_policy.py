# Copyright: (c) 2026, Everpure Ansible Team <pure-ansible-team@everpuredata.com>
# GNU General Public License v3.0+ (see COPYING.GPLv3 or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for purefb_policy context_names / fleet handling."""

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
sys.modules[
    "ansible_collections.purestorage.flashblade.plugins.module_utils.time_utils"
] = MagicMock()

from plugins.modules.purefb_policy import rename_smb_share_policy


def _module(context):
    module = Mock()
    module.check_mode = False
    module.params = {
        "name": "share_pol",
        "rename": "share_pol2",
        "context": context,
    }
    module.fail_json = Mock(side_effect=SystemExit("fail_json called"))
    module.exit_json = Mock()
    return module


def _blade():
    blade = Mock()
    # Array supports the context API version (2.17+)
    blade.get_versions.return_value.items = ["2.17"]
    ok = Mock()
    ok.status_code = 200
    blade.patch_smb_share_policies.return_value = ok
    return blade


class TestPolicyContextGating:
    """context_names must only be sent when a context is set."""

    def test_no_context_omits_context_names(self):
        """Standalone array (no context) must not send context_names."""
        module = _module(context="")
        blade = _blade()

        rename_smb_share_policy(module, blade)

        blade.patch_smb_share_policies.assert_called_once()
        assert "context_names" not in blade.patch_smb_share_policies.call_args[1]
        module.exit_json.assert_called_once_with(changed=True)

    def test_with_context_sends_context_names(self):
        """When a context is set, context_names must be sent."""
        module = _module(context="member-array")
        blade = _blade()

        rename_smb_share_policy(module, blade)

        blade.patch_smb_share_policies.assert_called_once()
        assert blade.patch_smb_share_policies.call_args[1]["context_names"] == [
            "member-array"
        ]

from plugins.plugin_loader import load_default_plugins
print("plugins import OK")
from integrations.integration_loader import load_default_integrations
print("integrations import OK")
load_default_plugins()
print("plugins loaded OK")
load_default_integrations()
print("integrations loaded OK")

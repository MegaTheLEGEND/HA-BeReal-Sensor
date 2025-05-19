import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from .const import DOMAIN


class BeRealConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for the BeReal integration."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step of the config flow for BeReal."""
        errors = {}

        if user_input is not None:
            # If valid, create the entry
            return self.async_create_entry(
                title=f"BeReal: {user_input['region']}", data=user_input
            )

        # Show config form
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required("region", default="us-central"): str,
                }
            ),
            errors=errors,
        )

"""Enter generated account passwords without exposing them as Robot keyword arguments."""

from robot.libraries.BuiltIn import BuiltIn


class AccountSecrets:
    def enter_account_password(self, role, selector):
        """Fill a password from the process environment for an allowed fixture role; return nothing."""
        if role not in ("ADMIN", "CUSTOMER", "SELLER"):
            raise ValueError("Choose ADMIN, CUSTOMER or SELLER.")
        browser = BuiltIn().get_library_instance("Browser")
        browser.fill_secret(selector, "%ROBOT_" + role + "_PASSWORD")

"""Use native Shuup commerce views with a dedicated fragrance-house presentation."""
from shuup.themes.classic_gray.theme import ClassicGrayTheme


class FuzcakeTheme(ClassicGrayTheme):
    identifier = "storefront.fuzcake"
    name = "fuzcake Fragrance House"
    author = "Robot Web Tests"
    template_dir = "fuzcake"
    default_template_dir = "classic_gray"

    def get_view(self, view_name):
        """Keep old collection links compatible by delegating to the native catalogue view."""
        if view_name == "products":
            from shuup.front.views.category import AllCategoriesView

            return AllCategoriesView
        return super(FuzcakeTheme, self).get_view(view_name)

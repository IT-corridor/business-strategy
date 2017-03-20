from __future__ import unicode_literals

from django.conf.urls import include, url
from django.conf.urls.i18n import i18n_patterns
from django.contrib import admin
from django.views.i18n import set_language

from mezzanine.core.views import direct_to_template
from mezzanine.conf import settings

from general.views import *

admin.autodiscover()

# Add the urlpatterns for any custom Django applications here.
# You can also change the ``home`` view to add your own functionality
# to the project's homepage.

urlpatterns = i18n_patterns(
    # Change the admin prefix here to use an alternate URL for the
    # admin interface, which would be marginally more secure.
    url("^admin/", include(admin.site.urls)),
)

if settings.USE_MODELTRANSLATION:
    urlpatterns += [
        url('^i18n/$', set_language, name='set_language'),
    ]

urlpatterns += [
    url("^$", direct_to_template, {"template": "index.html"}, name="home"),
    url(r"^login", user_login, name="login"),
    url(r"^logout", user_logout, name="logout"),
    url(r"^enterprise", enterprise, name="enterprise"),
    url(r"^_enterprise", ajax_enterprise, name="_enterprise"),
    url(r"^get_num_employers", get_num_employers, name="get_num_employers"),
    url("^", include("mezzanine.urls")),

    url(r"^import_employer", import_employer, name="import_employer"),
    url(r"^import_life", import_life, name="import_life"),
    url(r"^import_std", import_std, name="import_std"),

    url(r"^print_template", print_template, name="print_template"),
    url(r"^print_pdf", print_pdf, name="print_pdf"),
    url(r"^wkhtml_pdf", PDFView.as_view(), name="wkhtml_pdf"),
]

# Adds ``STATIC_URL`` to the context of error pages, so that error
# pages can use JS, CSS and images.
handler404 = "mezzanine.core.views.page_not_found"
handler500 = "mezzanine.core.views.server_error"

# Standard library
import os
from json import loads

# Packages
import flask
import talisker.requests
import pycountry
from canonicalwebteam.launchpad import Launchpad

# Local
from webapp.api import dashboard as api
from webapp.api.exceptions import ApiError, ApiResponseErrorList
from webapp.decorators import login_required
from webapp.publisher.snaps import logic
from webapp.publisher.views import _handle_error, _handle_error_list

launchpad = Launchpad(
    username=os.getenv("LP_API_USERNAME"),
    token=os.getenv("LP_API_TOKEN"),
    secret=os.getenv("LP_API_TOKEN_SECRET"),
    session=talisker.requests.get_session(),
)


@login_required
def get_settings(snap_name):
    try:
        snap_details = api.get_snap_info(snap_name, flask.session)
    except ApiResponseErrorList as api_response_error_list:
        if api_response_error_list.status_code == 404:
            return flask.abort(404, "No snap named {}".format(snap_name))
        else:
            return _handle_error_list(api_response_error_list.errors)
    except ApiError as api_error:
        return _handle_error(api_error)

    if "whitelist_country_codes" in snap_details:
        whitelist_country_codes = (
            snap_details["whitelist_country_codes"]
            if len(snap_details["whitelist_country_codes"]) > 0
            else []
        )
    else:
        whitelist_country_codes = []

    if "blacklist_country_codes" in snap_details:
        blacklist_country_codes = (
            snap_details["blacklist_country_codes"]
            if len(snap_details["blacklist_country_codes"]) > 0
            else []
        )
    else:
        blacklist_country_codes = []

    countries = []
    for country in pycountry.countries:
        countries.append({"key": country.alpha_2, "name": country.name})

    is_on_lp = False
    lp_snap = launchpad.get_snap_by_store_name(snap_name)
    if lp_snap:
        is_on_lp = True

    context = {
        "snap_name": snap_details["snap_name"],
        "snap_title": snap_details["title"],
        "snap_id": snap_details["snap_id"],
        "publisher_name": snap_details["publisher"]["display-name"],
        "license": license,
        "private": snap_details["private"],
        "unlisted": snap_details["unlisted"],
        "countries": countries,
        "whitelist_country_codes": whitelist_country_codes,
        "blacklist_country_codes": blacklist_country_codes,
        "price": snap_details["price"],
        "store": snap_details["store"],
        "keywords": snap_details["keywords"],
        "status": snap_details["status"],
        "is_on_lp": is_on_lp,
    }

    return flask.render_template("publisher/settings.html", **context)


@login_required
def post_settings(snap_name):
    changes = None
    changed_fields = flask.request.form.get("changes")

    if changed_fields:
        changes = loads(changed_fields)

    if changes:
        snap_id = flask.request.form.get("snap_id")
        error_list = []

        body_json = logic.filter_changes_data(changes)

        if body_json:
            try:
                api.snap_metadata(snap_id, flask.session, body_json)
            except ApiResponseErrorList as api_response_error_list:
                if api_response_error_list.status_code == 404:
                    return flask.abort(
                        404, "No snap named {}".format(snap_name)
                    )
                else:
                    error_list = error_list + api_response_error_list.errors
            except ApiError as api_error:
                return _handle_error(api_error)

        if error_list:
            try:
                snap_details = api.get_snap_info(snap_name, flask.session)
            except ApiResponseErrorList as api_response_error_list:
                if api_response_error_list.status_code == 404:
                    return flask.abort(
                        404, "No snap named {}".format(snap_name)
                    )
                else:
                    error_list = error_list + api_response_error_list.errors
            except ApiError as api_error:
                return _handle_error(api_error)

            field_errors, other_errors = logic.invalid_field_errors(error_list)

            countries = []
            for country in pycountry.countries:
                countries.append(
                    {"key": country.alpha_2, "name": country.name}
                )

            is_on_lp = False
            lp_snap = launchpad.get_snap_by_store_name(
                snap_details["snap_name"]
            )
            if lp_snap:
                is_on_lp = True

            if "whitelist_country_codes" in snap_details:
                whitelist_country_codes = (
                    snap_details["whitelist_country_codes"]
                    if len(snap_details["whitelist_country_codes"]) > 0
                    else []
                )
            else:
                whitelist_country_codes = []

            if "blacklist_country_codes" in snap_details:
                blacklist_country_codes = (
                    snap_details["blacklist_country_codes"]
                    if len(snap_details["blacklist_country_codes"]) > 0
                    else []
                )
            else:
                blacklist_country_codes = []

            context = {
                # read-only values from details API
                "snap_name": snap_details["snap_name"],
                "snap_title": snap_details["title"],
                "publisher_name": snap_details["publisher"]["display-name"],
                "snap_id": snap_details["snap_id"],
                "private": snap_details["private"],
                "unlisted": snap_details["unlisted"],
                "countries": countries,
                "whitelist_country_codes": whitelist_country_codes,
                "blacklist_country_codes": blacklist_country_codes,
                "price": snap_details["price"],
                "store": snap_details["store"],
                "keywords": snap_details["keywords"],
                "status": snap_details["status"],
                "is_on_lp": is_on_lp,
                # errors
                "error_list": error_list,
                "field_errors": field_errors,
                "other_errors": other_errors,
            }

            return flask.render_template("publisher/settings.html", **context)

        flask.flash("Changes applied successfully.", "positive")
    else:
        flask.flash("No changes to save.", "information")

    return flask.redirect(flask.url_for(".get_settings", snap_name=snap_name))

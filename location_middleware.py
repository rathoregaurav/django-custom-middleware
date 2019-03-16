from django.core.exceptions import PermissionDenied
from rest_framework.status import HTTP_412_PRECONDITION_FAILED
from rest_framework.response import Response
from location_manager.models import CountryMaster
from django.db.models import Q
from django.utils.deprecation import MiddlewareMixin
import ast
from django.core.exceptions import ImproperlyConfigured
import re
from pytz import country_timezones, timezone
from datetime import datetime
import json

class CheckCountry(MiddlewareMixin):

  def country_timezone_incorrect_get_default(self):
    if self.timezone_list and isinstance(self.timezone_list, list):
      tz = timezone(self.timezone_list[0])
      local_datetime_now = datetime.now(tz).replace(tzinfo=None)
      is_current_location_service_allowed = CountryMaster.objects.filter(
          status=1, active_status=1).filter(
          id=self.country_id, 
          start_date__lte=local_datetime_now,
          end_date__gte=local_datetime_now)
      if is_current_location_service_allowed:
        return True
    return False

  def check_timezone_count_in_country(self):
    self.timezone_list = country_timezones.get(self.iso, None)
    if not self.timezone_list:
      return False
    if self.location_timezone in self.timezone_list:
      tz = timezone(self.location_timezone)
      local_datetime_now = datetime.now(tz).replace(tzinfo=None)
      is_current_location_service_allowed = CountryMaster.objects.filter(
          id=self.country_id, 
          start_date__lte=local_datetime_now,
          end_date__gte=local_datetime_now)
      if is_current_location_service_allowed:
        return True
      return False
    if self.country_timezone_incorrect_get_default():
      return True
    return False

  def check_country_approval(self, **kwargs):
    have_country_data = CountryMaster.objects.filter(
      status=1, active_status=1).filter(
      Q(country__iexact=kwargs["country_long_name"]) | 
          Q(iso__iexact=kwargs["country_short_name"])
          ).first()
    if have_country_data:
      if not have_country_data.is_time_approval_required:
        return True
      self.iso = kwargs["country_short_name"]
      self.country_id = have_country_data.id
      if self.check_timezone_count_in_country():
        return True
      return False
    else:
      return False

  def process_request(self, request):
    if request.path.startswith('/api/'):
      if 'application/json' in request.META['CONTENT_TYPE']:
        self.country_long_name = request.GET.get("country_long_name", None)
        self.country_short_name = request.GET.get("country_short_name", None)
        self.location_timezone = request.GET.get("location_timezone", None)

        if self.country_long_name and self.country_short_name and self.location_timezone:
          if self.check_country_approval(country_long_name=self.country_long_name, 
                country_short_name=self.country_short_name,
                location_timezone=self.location_timezone):
            return
          else:
            raise PermissionDenied

        if hasattr(request, 'body'):
          request_data = request.body
          request_data_string = str(request_data)
          if request_data:
            if (re.search("country_long_name", request_data_string) and 
                re.search("country_short_name", request_data_string) and 
                re.search("location_timezone", request_data_string)):
              request_data_dict = request_data.decode('utf-8')
              request_data_dict = json.loads(request_data_dict)
              self.country_long_name = request_data_dict.get("country_long_name", None)
              self.country_short_name = request_data_dict.get("country_short_name", None)
              self.location_timezone = request_data_dict.get("location_timezone", None)
              if self.country_long_name and self.country_short_name and self.location_timezone:
                if self.check_country_approval(country_long_name=self.country_long_name, 
                      country_short_name=self.country_short_name,
                      location_timezone=self.location_timezone):
                  return
                else:
                  raise PermissionDenied
              else:
                raise PermissionDenied
            raise PermissionDenied
      else:
        country_long_name_post = request.POST.get("country_long_name", None)
        country_short_name_post = request.POST.get("country_short_name", None)
        location_timezone_post = request.POST.get("location_timezone", None)

        country_long_name_get = request.GET.get("country_long_name", None)
        country_short_name_get = request.GET.get("country_short_name", None)
        location_timezone_get = request.GET.get("location_timezone", None)

        self.country_long_name = country_long_name_post if country_long_name_post else country_long_name_get
        self.country_short_name = country_short_name_post if country_short_name_post else country_short_name_get
        self.location_timezone = location_timezone_post if location_timezone_post else location_timezone_get

        if self.country_long_name and self.country_short_name and self.location_timezone:
          if self.check_country_approval(country_long_name=self.country_long_name, 
                country_short_name=self.country_short_name,
                location_timezone=self.location_timezone):
            return
          else:
            raise PermissionDenied
        else:
          raise PermissionDenied

    else:
      return

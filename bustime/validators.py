import datetime
from django.core.exceptions import ValidationError
from django.utils.deconstruct import deconstructible


@deconstructible
class DateValidator():
    MESSAGE = "Дата (%(value)s) должна быть {operator} '%(date)s'"

    MSG_BEFORE = 'меньше'

    MSG_AFTER = 'больше'

    DATETIME_FORMAT = '%Y-%m-%d %H:%M'

    def __init__(self, date, after=False, equal=False):
        """
        Stores validator config.
        *date* must either be a :cls:`datetime.datetime` object, or a callable
        that returns such object.
        If *after* is set, the checked date must be after the stored *date*
        instead of before and if *equal* is set, equality is accepted.
        """
        self.date = date
        self.after = after
        self.equal = equal
        self.message = self.MESSAGE.format(
            operator=self.MSG_AFTER if after else self.MSG_BEFORE
        )

    def __eq__(self, other):
        if (self.date == other.date and 
            self.after == other.after and 
            self.equal == other.equal):
            return True
        return False

    def __call__(self, value):
        # get min/max date
        try:
            date = self.date()
        except TypeError:
            date = self.date
        # check
        if self.equal and value == date:
            return
        if self.after:
            if value > date:
                return
        else:
            if value < date:
                return
        raise ValidationError(
            self.message, code='invalid', params={
                'value': value.strftime(self.DATETIME_FORMAT),
                'date': date.strftime(self.DATETIME_FORMAT)
            }
        )

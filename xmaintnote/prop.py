import logging

from icalendar import vText

from xmaintnote.util import register_property
from xmaintnote.exc import PropertyError

LOGGER = logging.getLogger(__name__)


@register_property
class vXMaintNoteImpact(vText):
    """X-MAINTNOTE-IMPACT"""
    property_name = 'x-maintnote-impact'
    # list of known impact types
    impact_types = [
        'NO-IMPACT',
        'REDUCED-REDUNDANCY',
        'DEGRADED',
        'OUTAGE'
    ]

    def __init__(self, *args, **kwargs):
        if str(self) not in self.impact_types:
            LOGGER.error(
                'Unrecognised impact type %r should be treated as OUTAGE',
                str(self))


@register_property
class vXMaintNoteStatus(vText):
    """X-MAINTNOTE-STATUS"""
    property_name = 'x-maintnote-status'
    allowed_values = (
        'TENTATIVE',
        'CONFIRMED',
        'CANCELLED',
        'IN-PROCESS',
        'COMPLETED',
    )

    def __init__(self, *args, **kwargs):
        if str(self) not in self.allowed_values:
            LOGGER.error('Encountered non-standard %s status value %s',
                         self.property_name, str(self))
            raise PropertyError()
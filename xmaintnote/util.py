import simplejson as _json
import icalendar


def encode_vDDDTypes(obj):
    if isinstance(obj, icalendar.prop.vDDDTypes):
        # convert vDDDTypes - date/time types to strings
        return unicode(obj.to_ical())
    raise TypeError(repr(o) + " is not JSON serializable")


def ical2json(cal):
    data = {}
    data[cal.name] = dict(cal.items());
    
    for component in cal.subcomponents:
        if not data[cal.name].has_key(component.name):
            data[cal.name][component.name] = []

            comp_obj = {}
            for item in component.items():
                comp_obj[item[0]] = unicode(item[1])

        data[cal.name][component.name].append(comp_obj)

    json = _json.dumps(data, default=encode_vDDDTypes, sort_keys=True, indent='    ')

    return json


def display(cal):
    return cal.to_ical().replace('\r\n', '\n').strip()

import json

import icalendar


def encode_vDDDTypes(obj):
    if isinstance(obj, icalendar.prop.vDDDTypes):
        # convert vDDDTypes - date/time types to strings
        return obj.to_ical()
    raise TypeError(repr(obj) + " is not JSON serializable")


def ical2json(cal):
    data = {cal.name: dict(cal.items())}

    for component in cal.subcomponents:
        if component.name not in data[cal.name]:
            data[cal.name][component.name] = []

            comp_obj = {}
            for item in component.items():
                comp_obj[item[0]] = item[1]

        data[cal.name][component.name].append(comp_obj)

    return json.dumps(data, default=encode_vDDDTypes, sort_keys=True, indent=4)


def display(cal):
    return cal.to_ical().replace('\r\n', '\n').strip()


def register_property(property_type):
    property_name = property_type.property_name
    icalendar.cal.types_factory[property_name] = property_type
    icalendar.cal.types_factory.types_map[property_name] = property_name
    return property_type

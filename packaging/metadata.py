import re
import json
from email.message import EmailMessage
from email import message_from_string
from collections import namedtuple

class InvalidMetadata(Exception):
    pass

Field = namedtuple("Field", ["field", "attr", "multi", "mandatory"])

def attr_name(field):
    return field.lower().replace("-", "_")

FIELDS = [
    # Field, Multi-Use, Mandatory
    ("Metadata-Version", False, True),
    ("Name", False, True),
    ("Version", False, True),
    ("Platform", True, False),
    ("Supported-Platform", True, False),
    ("Summary", False, False),
    ("Description", False, False),
    ("Description-Content-Type", False, False),
    # Technically, Keywords is not multi-use, but this API
    # treats it as if it is.
    ("Keywords", True, False),
    ("Home-page", False, False),
    ("Download-URL", False, False),
    ("Author", False, False),
    ("Author-email", False, False),
    ("Maintainer", False, False),
    ("Maintainer-email", False, False),
    ("License", False, False),
    ("Classifier", True, False),
    ("Requires-Dist", True, False),
    ("Requires-Python", False, False),
    ("Requires-External", True, False),
    ("Project-URL", True, False),
    ("Provides-Extra", True, False),
    ("Provides-Dist", True, False),
    ("Obsoletes-Dist", True, False),
]

FIELDS = [
    Field(field, attr_name(field), multi, mandatory)
    for field, multi, mandatory in FIELDS
]

FIELDS_BY_ATTR = {f.attr: f for f in FIELDS}
FIELDS_BY_NAME = {f.field: f for f in FIELDS}

class Metadata:
    def __init__(self, **kw):
        self.metadata = kw
        self.validate()
    def validate(self):
        mandatory = {f.attr for f in FIELDS if f.mandatory}


SINGLE_USE = [
    "Metadata-Version",
    "Name",
    "Version",
    "Summary",
    "Description",
    "Description-Content-Type",
    "Home-page",
    "Download-URL",
    "Author",
    "Author-email",
    "Maintainer",
    "Maintainer-email",
    "License",
    "Requires-Python",
]

MULTIPLE_USE = [
    "Platform",
    "Supported-Platform",
    "Classifier",
    "Requires-Dist",
    "Requires-External",
    "Project-URL",
    "Provides-Extra",
    "Provides-Dist",
    "Obsoletes-Dist",

    # Technically single-use, but handled specially
    "Keywords",
]


SINGLE_USE_KEYS = set(json_form(k) for k in SINGLE_USE)
MULTIPLE_USE_KEYS = set(json_form(k) for k in MULTIPLE_USE)

def validate_metadata_dict(meta):
    for key, val in meta.items():
        if key in SINGLE_USE_KEYS:
            if not isinstance(val, str):
                raise InvalidMetadata(f"Non-string value for {key}: {val}")
        elif key in MULTIPLE_USE_KEYS:
            if not isinstance(val, list):
                raise InvalidMetadata(f"Non-list value for {key}: {val}")
        else:
            raise InvalidMetadata(f"Unknown key {key}: {val}")

class Metadata:
    def __init__(self, **kw):
        validate_metadata_dict(kw)
        self.metadata = kw

    def __eq__(self, other):
        if isinstance(other, Metadata):
            return self.metadata == other.metadata

    @classmethod
    def from_json(cls, data):
        return cls(**json.loads(data))

    @classmethod
    def from_rfc822(cls, data):
        metadata = {}
        msg = message_from_string(data)
        for field in SINGLE_USE:
            value = msg.get(field)
            if value:
                metadata[json_form(field)] = value
        for field in MULTIPLE_USE:
            value = msg.get_all(field)
            if value and len(value) > 0:
                if field == "Keywords":
                    if len(value) > 1:
                        raise InvalidMetadata
                    value = re.split(r"\s*(?:,|\s)\s*", value[0])
                metadata[json_form(field)] = value

        payload = msg.get_payload()
        if payload:
            if "description" in metadata:
                print("Both Description and payload given - ignoring Description")
            metadata["description"] = payload

        return cls(**metadata)

    def as_json(self):
        return json.dumps(self.metadata)

    def as_rfc822(self):
        msg = EmailMessage()
        for field in SINGLE_USE + MULTIPLE_USE:
            value = self.metadata.get(json_form(field))
            if value:
                if field == "Description":
                    # Special case - put in payload
                    msg.set_payload(value)
                    continue
                if field == "Keywords":
                    value = ", ".join(value)
                if isinstance(value, str):
                    value = [value]
                for item in value:
                    msg.add_header(field, item)

        return msg.as_string()

if __name__ == '__main__':
    m = Metadata(name="foo", version="1.0", keywords=["a", "b", "c"], description="Hello\nworld")
    rfc822_data = m.as_rfc822()
    json_data = m.as_json()
    print(rfc822_data)
    print(json_data)
    m2 = Metadata.from_json(json_data)
    m3 = Metadata.from_rfc822(rfc822_data)
    assert m == m2, "Metadata changed"
    assert m == m3, "Metadata changed"

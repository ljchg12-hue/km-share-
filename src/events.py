import json

def serialize_event(event):
    """Serializes an event dictionary to a JSON string with newline delimiter."""
    return (json.dumps(event) + '\n').encode('utf-8')

def deserialize_event(data):
    """Deserializes a JSON string to an event dictionary."""
    return json.loads(data.decode('utf-8'))

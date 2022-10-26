from typing import Any
from pymongo.collection import Collection

UUID4_PLACEHOLDER = "be8b61ee-48b1-4624-bf7a-2ca31f7c5ef4"


def value_in_database(name: str, default_value: Any) -> property:
    """Property factory to mirror a Device attribute in the ALab database. This must be declared as a Class Variable under a Device subclass of BaseDevice!

    Args:
        name (str): attribute name
        default_value (Any): default value for the attribute. Note that this value is not used until the first time a property is queried; at this time, if the attribute is not found in the database, it is set to this value.

    Returns:
        property: class property that handles getting/setting values from the database.


    Example usage when defining a new Device:

        .. code-block:: python
        from alab_management.device_view import BaseDevice, attribute_in_database

        class MyDevice(BaseDevice):
            my_attribute = attribute_in_database("my_attribute", 0)

            def __init__(self, name: str, **kwargs):
                super().__init__(name, **kwargs)
                self.name = name
                self.my_attribute #initial call to the property, which sets the default value in the database

        ....
        #first instantiation

        mydevice = MyDevice(name = "mydevice_1")
        mydevice.my_attribute = 5 #sets the value in the database

        ....
        #future instantiation
        mydevice = MyDevice(name = "mydevice_1")
        mydevice.my_attribute #retrieves value from db and returns 5


    """

    def getter(self) -> Any:
        attributes = self._device_view.get_all_attributes(device_name=self.name)
        if name not in attributes:
            attributes[name] = default_value
            self._device_view.set_all_attributes(self.name, attributes=attributes)
        return attributes[name]

    def setter(self, value: Any) -> None:
        self._device_view.set_attribute(
            device_name=self.name, attribute=name, value=value
        )

    return property(getter, setter)


class ListInDatabase:
    """Class that emulates a list, but stores the list in the device database. Useful for working with Device attributes that are lists, so values persist across alabos sessions. This should be instantiated using `alab_management.device_view.device.BaseDevice.dict_in_database`"""

    def __init__(
        self,
        device_collection: Collection,
        device_name: str,
        attribute_name: str,
        default_value: list = None,
    ):
        self._collection = device_collection
        self.attribute_name = attribute_name
        self.device_name = device_name
        if default_value is None:
            self.default_value = []
        else:
            if not isinstance(default_value, list):
                raise ValueError("Default value for ListInDatabase must be a list!")
            self.default_value = default_value

        result = self._collection.find_one(self.db_filter)
        if result is None:
            raise ValueError(
                f"A device by the name {self.device_name} was not found in the collection."
            )
        if self.attribute_name not in result["attributes"]:
            self._collection.update_one(
                self.db_filter, {"$set": {self.db_path: default_value}}
            )

    @property
    def db_path(self):
        return f"attributes.{self.attribute_name}"

    @property
    def db_filter(self):
        return {"name": self.device_name}

    @property
    def _value(self):
        value = self._collection.find_one(
            {"name": self.device_name}, projection=[self.db_path]
        )
        if value is None:
            raise ValueError(
                f"Device {self.device_name} does not contain data at {self.db_path}!"
            )
        return value["attributes"][self.attribute_name]

    def append(self, x):
        self._collection.update_one(self.db_filter, {"$push": {self.db_path: x}})

    def extend(self, x):
        current = self._value
        current.extend(x)
        self._collection.update_one(self.db_filter, {"$set": {self.db_path: current}})

    def clear(self):
        self._collection.update_one(self.db_filter, {"$set": {self.db_path: []}})

    def copy(self):
        return self._value  # copied by virtue of reading from database

    def index(self, x, start=None, stop=None):
        return self._value.index(x, start, stop)

    def count(self):
        return self._value.count()

    def insert(self, i, x):
        current = self._value
        current.insert(i, x)
        self._collection.update_one(self.db_filter, {"$set": {self.db_path: current}})

    def pop(self, i=-1):
        current = self._value
        result = current.pop(i)
        self._collection.update_one(self.db_filter, {"$set": {self.db_path: current}})
        return result

    def remove(self, x):
        current = self._value
        current.remove(x)
        self._collection.update_one(self.db_filter, {"$set": {self.db_path: current}})

    def reverse(self):
        current = self._value
        current.reverse()
        self._collection.update_one(self.db_filter, {"$set": {self.db_path: current}})

    def sort(self, key=None, reverse=False):
        current = self._value
        current.sort(key, reverse)
        self._collection.update_one(self.db_filter, {"$set": {self.db_path: current}})

    def __repr__(self):
        return str(self._value)

    def __str__(self):
        return str(self._value)

    def __add__(self, x):
        return self._value + x

    def __iadd__(self, x):
        new = self._value + x
        self._collection.update_one(self.db_filter, {"$set": {self.db_path: new}})
        return self

    def __mul__(self, x):
        return self._value * x

    def __imul__(self, x):
        new = self._value * x
        self._collection.update_one(self.db_filter, {"$set": {self.db_path: new}})
        return self

    def __getitem__(self, x):
        return self._value[x]

    def __setitem__(self, x, val):
        current = self._value
        current[x] = val
        self._collection.update_one(self.db_filter, {"$set": {self.db_path: current}})

    def __len__(self):
        return len(self._value)

    def __contains__(self, x):
        return x in self._value


class DictInDatabase:
    """Class that emulates a dict, but stores the dict in the device database. Useful for working with Device attributes that are dict, so values persist across alabos sessions. This should be instantiated using `alab_management.device_view.device.BaseDevice.dict_in_database`"""

    def __init__(
        self,
        device_collection: Collection,
        device_name: str,
        attribute_name: str,
        default_value: dict = None,
    ):
        self._collection = device_collection
        self.attribute_name = attribute_name
        self.device_name = device_name
        if default_value is None:
            self.default_value = {}
        else:
            if not isinstance(default_value, dict):
                raise ValueError(
                    "Default value for DictInDatabase must be a dictionary!"
                )
            self.default_value = default_value

        result = self._collection.find_one(self.db_filter)
        if result is None:
            raise ValueError(
                f"A device by the name {self.device_name} was not found in the collection."
            )
        if self.attribute_name not in result["attributes"]:
            self._collection.update_one(
                self.db_filter, {"$set": {self.db_path: self.default_value}}
            )

    @property
    def db_path(self):
        return f"attributes.{self.attribute_name}"

    @property
    def db_filter(self):
        return {"name": self.device_name}

    @property
    def _value(self):
        value = self._collection.find_one(
            {"name": self.device_name}, projection=[self.db_path]
        )
        if value is None:
            raise ValueError(
                f"Device {self.device_name} does not contain data at {self.db_path}!"
            )
        return value["attributes"][self.attribute_name]

    def clear(self):
        self._collection.update_one(self.db_filter, {"$set": {self.db_path: {}}})

    def copy(self):
        return self._value  # copied by virtue of reading from database

    def fromkeys(self):
        raise NotImplementedError("fromkeys is not implemented for DictInDatabase")

    def get(self, key, default=None):
        return self._value.get(key, default)

    def items(self):
        return self._value.items()

    def keys(self):
        return self._value.keys()

    def values(self):
        return self._value.values()

    def pop(self, key, default=UUID4_PLACEHOLDER):
        current = self._value
        result = current.pop(key, default)
        if result == UUID4_PLACEHOLDER:  # only fires if default value was not provided
            raise KeyError(f"{key} was not found in the dictionary!")

        self._collection.update_one(self.db_filter, {"$set": {self.db_path: current}})
        return result

    def popitem(self):
        current = self._value
        result = current.popitem()
        self._collection.update_one(self.db_filter, {"$set": {self.db_path: current}})
        return result

    def setdefault(self, key, default=None):
        raise NotImplementedError("setdefault is not implemented for DictInDatabase")

    def update(self, *args, **kwargs):
        current = self._value
        current.update(*args, **kwargs)
        self._collection.update_one(self.db_filter, {"$set": {self.db_path: current}})

    def __reversed__(self):
        return reversed(self._value)

    def __iter__(self):
        return iter(self._value)

    def __repr__(self):
        return str(self._value)

    def __str__(self):
        return str(self._value)

    def __getitem__(self, x):
        return self._value[x]

    def __setitem__(self, x, val):
        current = self._value
        current[x] = val
        self._collection.update_one(self.db_filter, {"$set": {self.db_path: current}})

    def __delitem__(self, x):
        current = self._value
        del current[x]
        self._collection.update_one(self.db_filter, {"$set": {self.db_path: current}})

    def __contains__(self, x):
        return x in self._value

    def __len__(self):
        return len(self._value)


# TODO maybe update along the lines of https://github.com/zeycus/mongo_shelve/blob/master/mongo_shelve/mongo_shelve_class.py
def attribute_in_database(name: str, default_value: Any) -> property:
    """Property factory to mirror a Device attribute in the ALab database

    Args:
        name (str): attribute name
        default_value (Any): default value for the attribute. Note that this value is not used until the first time a property is queried; at this time, if the attribute is not found in the database, it is set to this value.

    Returns:
        property: class property that handles getting/setting values from the database.


    Example usage when defining a new Device:

        .. code-block:: python
        from alab_management.device_view import BaseDevice, attribute_in_database

        class MyDevice(BaseDevice):
            my_attribute = attribute_in_database("my_attribute", 0)

            def __init__(self, name: str, **kwargs):
                super().__init__(name, **kwargs)
                self.name = name
                self.my_attribute #initial call to the property, which sets the default value in the database

        ....
        #first instantiation

        mydevice = MyDevice(name = "mydevice_1")
        mydevice.my_attribute = 5 #sets the value in the database

        ....
        #future instantiation
        mydevice = MyDevice(name = "mydevice_1")
        mydevice.my_attribute #retrieves value from db and returns 5


    """

    def getter(self) -> Any:
        attributes = self._device_view.get_all_attributes(device_name=self.name)
        if name not in attributes:
            attributes[name] = default_value
            self._device_view.set_all_attributes(self.name, attributes=attributes)
        return attributes[name]

    def setter(self, value: Any) -> None:
        self._device_view.set_attribute(
            device_name=self.name, attribute=name, value=value
        )

    return property(getter, setter)

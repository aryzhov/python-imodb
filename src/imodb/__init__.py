import collections
import sys


class Field:

    def __init__(self, is_key=False, default=None, update=True, update_refs=True, hidden_field_name=None):
        self.is_key = is_key
        self.default = default
        self.update = update
        self.update_refs = update_refs
        self.name = None
        self.hidden_field_name = hidden_field_name
        self.meta = None

    def init(self, name, meta):
        self.name = name
        if self.hidden_field_name is None:
            self.hidden_field_name = '_' + name
        self.meta = meta

    def init_model(self, model):
        if not hasattr(model, self.hidden_field_name):
            default_value = self.default if not callable(self.default) else self.default()
            setattr(model, self.hidden_field_name, default_value)

    def getter(self, model):
        return getattr(model, self.hidden_field_name) if hasattr(model, self.hidden_field_name) else None

    def setter(self, model, value):
        old_value = self.getter(model)
        setattr(model, self.hidden_field_name, value)
        if self.update_refs and old_value is not None and old_value != value:
            for field in model.Meta.fields.values():
                if isinstance(field, ReferenceField):
                    if isinstance(field.reverse_ref, CollectionField):
                        if field.reverse_ref.ref_key is self:
                            ref = field.getter(model)
                            ref_collection = field.reverse_ref.getter(ref)
                            del ref_collection[old_value]
                            ref_collection[value] = model


class ReferenceField(Field):

    def __init__(self, ref_model=None, reverse_ref=None, hidden_field_name=None, update=False):
        super().__init__(is_key=False, default=None, update=update, hidden_field_name=hidden_field_name)
        self._ref_model = ref_model
        self._reverse_ref = reverse_ref

    @property
    def ref_model(self):
        """
        Returns the class of ref_model or None
        """
        if isinstance(self._ref_model, str):
            self._ref_model = getattr(sys.modules[self.meta.__module__], self._ref_model)
        return self._ref_model

    @property
    def reverse_ref(self):
        """
        Returns the reverse reference field or None
        """
        if isinstance(self._reverse_ref, str):
            self._reverse_ref = self.ref_model.Meta.fields[self._reverse_ref]
        return self._reverse_ref

    def setter(self, model, value):
        old_value = self.getter(model)
        if old_value is value:
            return
        if value is not None and not isinstance(value, self.ref_model):
            raise RuntimeError('Invalid reference class: {}, expected {}'.format(model.__class__, self.ref_model))
        super().setter(model, value)
        if old_value is not None:
            self.clear_reverse_ref(model, old_value)
        if value is not None:
            self.set_reverse_ref(model, value)

    def set_reverse_ref(self, model, ref_value):
        if self.reverse_ref is None:
            pass
        if isinstance(self.reverse_ref, CollectionField):
            collection = self.reverse_ref.getter(ref_value)
            collection += model
        else:
            self.reverse_ref.setter(ref_value, model)

    def clear_reverse_ref(self, model, ref_value):
        if self.reverse_ref is None or ref_value is None:
            pass
        if isinstance(self.reverse_ref, CollectionField):
            collection = self.reverse_ref.getter(ref_value)
            collection -= model
        else:
            if self.reverse_ref.getter(ref_value) is model:
                self.reverse_ref.setter(ref_value, None)


class ModelDict(collections.MutableMapping):

    def __init__(self, model, field):
        self.model = model
        self.field = field
        self._source_dict = None

    @property
    def source_dict(self):
        if self._source_dict is None:
            self._source_dict = self.field.dict_class()
        return self._source_dict

    @source_dict.setter
    def set_source_dict(self, value):
        self._source_dict = value

    def __getitem__(self, item):
        return self.source_dict.__getitem__(item)

    def __setitem__(self, key, value):
        old_value = None
        if key in self:
            old_value = self[key]
            if old_value is value:
                return
        self.source_dict.__setitem__(key, value)
        self.field.set_reverse_ref(self.model, value)
        if old_value is not None:
            self.field.clear_reverse_ref(self.model, old_value)

    def __delitem__(self, key):
        if key in self:
            old_value = self[key]
            self.source_dict.__delitem__(key)
            if old_value is not None:
                self.field.clear_reverse_ref(self.model, old_value)

    def __iter__(self):
        return self.source_dict.__iter__()

    def __len__(self):
        return len(self._source_dict) if self._source_dict else 0

    def __iadd__(self, value):
        key = self.field.get_ref_key(value)
        self[key] = value
        return self

    def __isub__(self, value):
        key = self.field.get_ref_key(value)
        if key in self and self[key] is value:
            del self[key]
        return self


class CollectionField(ReferenceField):

    def __init__(self, ref_model=None, ref_key=None, reverse_ref=None, dict_class=dict, hidden_field_name=None):
        super().__init__(ref_model=ref_model, reverse_ref=reverse_ref, hidden_field_name=hidden_field_name)
        self._ref_key = ref_key
        self.dict_class = dict_class

    def init_model(self, model):
        setattr(model, self.hidden_field_name, ModelDict(model, self))

    def setter(self, model, value):
        model_dict = self.getter(model)
        if not isinstance(value, ModelDict):
            model_dict.set_source_dict(value)

    @property
    def ref_key(self):
        if isinstance(self._ref_key, str):
            self._ref_key = self.ref_model.Meta.fields[self._ref_key]
        return self._ref_key or self.ref_model.Meta.key_field

    def get_ref_key(self, ref_value):
        if self.ref_key is None:
            raise RuntimeError("Key field not defined")
        return self.ref_key.getter(ref_value)


class ModelRegistry(type):

    def __new__(mcs, name, bases, namespace, **kwargs):
        fields = dict()
        key_field = None
        if bases:
            for base in bases:
                if hasattr(base, 'Meta'):
                    meta = base.Meta
                    fields.update(meta.fields)
                    if meta.key_field is not None:
                        if key_field is not None:
                            raise RuntimeError("Two base classes define a key field")
                        key_field = meta.key_field

        for field_name, field_value in namespace.items():
            if isinstance(field_value, Field):
                fields[field_name] = field_value
                if field_value.is_key:
                    if key_field:
                        raise RuntimeError("At most a single key field is allowed.")
                    key_field = field_value

        meta_class_namespace = {"fields": fields, "key_field": key_field, "__module__": namespace["__module__"]}
        meta_class = type.__new__(type, name+'.Meta', (object,), meta_class_namespace)
        namespace['Meta'] = meta_class

        for field_name, field in fields.items():
            if field.meta is None:
                field.init(field_name, meta_class)
                del namespace[field_name]

        result = type.__new__(mcs, name, bases, namespace, **kwargs)
        return result


class Model(metaclass=ModelRegistry):
    """
    Base class for models
    """
    class Meta:
        fields = dict()
        key_field = None

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
        for field in self.__class__.Meta.fields.values():
            field.init_model(self)

    def __getattr__(self, name):
        if name in self.__class__.Meta.fields:
            field = self.__class__.Meta.fields[name]
            return field.getter(self)
        else:
            return super().__getattr__(name)

    def __setattr__(self, name, value):
        if name in self.__class__.Meta.fields:
            field = self.__class__.Meta.fields[name]
            field.setter(self, value)
        else:
            super().__setattr__(name, value)

    def update(self, from_model):
        for field in self.__class__.Meta.fields.values():
            if field.update:
                field.setter(self, field.getter(from_model))

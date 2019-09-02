from abc import ABC
from typing import Iterable, List

from pydantic import BaseModel, create_model, Required


class Serializer(BaseModel):

    @classmethod
    def sanitize_list(cls, iterable: Iterable) -> List[dict]:
        def clean_d(d):
            for e in cls.Meta.exclude:
                d.pop(e)
            return d
        return list(map(lambda x: clean_d(x), iterable))

    async def save(self):
        instance = self.Meta.model(**self.__values__)
        await instance.save()
        self.id = instance.id
        return instance

    async def update_one(self, filter_kwargs):
        instance = self.Meta.model(**self.__values__)
        await instance.update_one(filter_kwargs=filter_kwargs, **self.dict())
        return instance

    def dict(self, *args, **kwargs) -> dict:
        exclude = kwargs.get('exclude')
        if not exclude:
            exclude = set()

        exclude.update({"_id"})

        if hasattr(self.Meta, "exclude"):
            exclude.update(self.Meta.exclude)

        if hasattr(self.Meta, "write_only_fields"):
            exclude.update(self.Meta.write_only_fields)

        kwargs.update({"exclude": exclude})
        original = super().dict(*args, **kwargs)
        return original


class AbstractMeta(ABC):
    exclude = ()
    model = None


class ModelSerializer(Serializer):

    def __new__(cls, *args, **kwargs):
        _fields = {}

        _Meta = getattr(cls, "Meta", type("Meta"))
        Meta = type("Meta", (_Meta, AbstractMeta), {})

        if hasattr(Meta, "model") and Meta.model is not None:
            for f, t in Meta.model.__fields__.items():
                if f not in Meta.exclude:
                    f_def = t.default
                    if t.required:
                        f_def = Required
                    _fields.update({f: (t.type_, f_def)})

        for f, t in cls.__fields__.items():
            if f not in Meta.exclude:
                f_def = t.default
                if t.required:
                    f_def = Required
                _fields.update({f: (t.type_, f_def)})

        new_model = create_model(cls.__name__, __base__=Serializer, **_fields)

        reserved_attrs = ["Meta"]
        for attr, value in cls.__dict__.items():
            if not attr.startswith("_") and attr not in reserved_attrs:
                setattr(new_model, attr, value)

        setattr(new_model, "Meta", Meta)

        return new_model(*args, **kwargs)

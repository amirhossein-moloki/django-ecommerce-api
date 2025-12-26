from types import SimpleNamespace

from .declarations import (
    Declaration,
    LazyAttribute,
    PostGenerationMethodCall,
    SelfAttribute,
)


class DjangoModelFactoryMeta(type):
    def __new__(mcls, name, bases, attrs):
        cls = super().__new__(mcls, name, bases, attrs)
        meta = attrs.get("Meta") or getattr(cls, "Meta", None)
        cls._meta = SimpleNamespace(model=getattr(meta, "model", None))
        cls._sequence = 0
        return cls

    def __call__(cls, *args, **kwargs):
        return cls.create(*args, **kwargs)


class DjangoModelFactory(metaclass=DjangoModelFactoryMeta):
    @classmethod
    def _next_sequence(cls):
        cls._sequence += 1
        return cls._sequence

    @classmethod
    def _collect_declarations(cls):
        declarations = {}
        for base in reversed(cls.__mro__):
            for key, value in getattr(base, "__dict__", {}).items():
                if key == "Meta":
                    continue
                if isinstance(value, Declaration) or getattr(
                    value, "_is_post_generation", False
                ):
                    declarations[key] = value
                    continue
                if isinstance(value, (classmethod, staticmethod, property)):
                    continue
                if not callable(value) and not isinstance(value, type):
                    declarations[key] = value
        return declarations

    @classmethod
    def build(cls, **kwargs):
        return cls._generate(create=False, **kwargs)

    @classmethod
    def create(cls, **kwargs):
        return cls._generate(create=True, **kwargs)

    @classmethod
    def create_batch(cls, size, **kwargs):
        return [cls.create(**kwargs) for _ in range(size)]

    @classmethod
    def _generate(cls, create, **kwargs):
        if not cls._meta.model:
            raise ValueError("Factory Meta.model is required")

        sequence = cls._next_sequence()
        declarations = cls._collect_declarations()
        attrs = dict(kwargs)
        pending_self_attrs = {}
        post_generation_calls = []
        post_generation_hooks = []

        for name, declaration in declarations.items():
            if name.startswith("_"):
                continue
            if name in attrs:
                continue
            if not isinstance(declaration, Declaration) and not getattr(
                declaration, "_is_post_generation", False
            ):
                attrs[name] = declaration
                continue
            if isinstance(declaration, SelfAttribute):
                pending_self_attrs[name] = declaration
                continue
            if isinstance(declaration, PostGenerationMethodCall):
                post_generation_calls.append((name, declaration))
                continue
            if getattr(declaration, "_is_post_generation", False):
                post_generation_hooks.append(declaration)
                continue
            if isinstance(declaration, LazyAttribute):
                attrs[name] = declaration.evaluate(attrs, sequence, create)
                continue
            if isinstance(declaration, Declaration):
                attrs[name] = declaration.evaluate(attrs, sequence, create)
                continue

        for name, declaration in pending_self_attrs.items():
            attrs[name] = declaration.evaluate(attrs, sequence, create)

        if create:
            instance = cls._meta.model.objects.create(**attrs)
        else:
            instance = cls._meta.model(**attrs)

        for _name, declaration in post_generation_calls:
            declaration.call(instance, create)
            if create:
                instance.save()

        for hook in post_generation_hooks:
            hook(instance, create, None)
            if create:
                instance.save()

        return instance

from types import SimpleNamespace

from faker import Faker as FakerProvider


class Declaration:
    def evaluate(self, attrs, sequence, create):
        raise NotImplementedError


class Faker(Declaration):
    def __init__(self, provider, **kwargs):
        self.provider = provider
        self.kwargs = kwargs
        self._faker = FakerProvider()

    def evaluate(self, attrs, sequence, create):
        provider = getattr(self._faker, self.provider)
        return provider(**self.kwargs) if self.kwargs else provider()


class Sequence(Declaration):
    def __init__(self, func):
        self.func = func

    def evaluate(self, attrs, sequence, create):
        return self.func(sequence)


class LazyAttribute(Declaration):
    def __init__(self, func):
        self.func = func

    def evaluate(self, attrs, sequence, create):
        return self.func(SimpleNamespace(**attrs))


class LazyFunction(Declaration):
    def __init__(self, func):
        self.func = func

    def evaluate(self, attrs, sequence, create):
        return self.func()


class SelfAttribute(Declaration):
    def __init__(self, attribute):
        self.attribute = attribute

    def evaluate(self, attrs, sequence, create):
        parts = self.attribute.strip(".").split(".")
        value = attrs
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            else:
                value = getattr(value, part)
        return value


class SubFactory(Declaration):
    def __init__(self, factory, **defaults):
        self.factory = factory
        self.defaults = defaults

    def evaluate(self, attrs, sequence, create):
        resolved = {}
        for key, value in self.defaults.items():
            if isinstance(value, SelfAttribute):
                resolved[key] = value.evaluate(attrs, sequence, create)
            else:
                resolved[key] = value
        if create:
            return self.factory.create(**resolved)
        return self.factory.build(**resolved)


class PostGenerationMethodCall(Declaration):
    def __init__(self, method_name, *args, **kwargs):
        self.method_name = method_name
        self.args = args
        self.kwargs = kwargs

    def evaluate(self, attrs, sequence, create):
        return None

    def call(self, obj, create):
        getattr(obj, self.method_name)(*self.args, **self.kwargs)


def post_generation(func):
    func._is_post_generation = True
    return func


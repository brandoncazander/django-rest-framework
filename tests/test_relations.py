from .utils import mock_reverse, fail_reverse, BadType, MockObject, MockQueryset
from django.conf.urls import patterns, url, include
from django.core.exceptions import ImproperlyConfigured, ObjectDoesNotExist
from rest_framework import serializers
from rest_framework.test import APISimpleTestCase, APIRequestFactory
import pytest

factory = APIRequestFactory()
request = factory.get('/')  # Just to ensure we have a request in the serializer context

dummy_view = lambda request, pk: None

included_patterns = [
    url(r'^example/(?P<pk>\d+)/$', dummy_view, name='example-detail')
]

urlpatterns = patterns(
    '',
    url(r'^v1/', include(included_patterns, namespace='v1')),
    url(r'^example/(?P<pk>\d+)/$', dummy_view, name='example-detail')
)


class TestStringRelatedField(APISimpleTestCase):
    def setUp(self):
        self.instance = MockObject(pk=1, name='foo')
        self.field = serializers.StringRelatedField()

    def test_string_related_representation(self):
        representation = self.field.to_representation(self.instance)
        assert representation == '<MockObject name=foo, pk=1>'


class TestPrimaryKeyRelatedField(APISimpleTestCase):
    def setUp(self):
        self.queryset = MockQueryset([
            MockObject(pk=1, name='foo'),
            MockObject(pk=2, name='bar'),
            MockObject(pk=3, name='baz')
        ])
        self.instance = self.queryset.items[2]
        self.field = serializers.PrimaryKeyRelatedField(queryset=self.queryset)

    def test_pk_related_lookup_exists(self):
        instance = self.field.to_internal_value(self.instance.pk)
        assert instance is self.instance

    def test_pk_related_lookup_does_not_exist(self):
        with pytest.raises(serializers.ValidationError) as excinfo:
            self.field.to_internal_value(4)
        msg = excinfo.value.detail[0]
        assert msg == 'Invalid pk "4" - object does not exist.'

    def test_pk_related_lookup_invalid_type(self):
        with pytest.raises(serializers.ValidationError) as excinfo:
            self.field.to_internal_value(BadType())
        msg = excinfo.value.detail[0]
        assert msg == 'Incorrect type. Expected pk value, received BadType.'

    def test_pk_representation(self):
        representation = self.field.to_representation(self.instance)
        assert representation == self.instance.pk


class TestHyperlinkedRelatedField(APISimpleTestCase):
    urls = 'tests.test_relations'

    def setUp(self):
        class HyperlinkedMockQueryset(MockQueryset):
            def get(self, **lookup):
                for item in self.items:
                    if item.pk == int(lookup.get('pk', -1)):
                        return item
                raise ObjectDoesNotExist()

        self.queryset = HyperlinkedMockQueryset([
            MockObject(pk=1, name='foo'),
            MockObject(pk=2, name='bar'),
            MockObject(pk=3, name='baz')
        ])
        self.field = serializers.HyperlinkedRelatedField(
            view_name='example-detail',
            queryset=self.queryset
        )
        self.field._context = {'request': request}

    def test_matching_url(self):
        self.field.to_internal_value('/example/3/')
        self.field.to_internal_value('/v1/example/3/')


class TestHyperlinkedIdentityField(APISimpleTestCase):
    def setUp(self):
        self.instance = MockObject(pk=1, name='foo')
        self.field = serializers.HyperlinkedIdentityField(view_name='example')
        self.field.reverse = mock_reverse
        self.field._context = {'request': True}

    def test_representation(self):
        representation = self.field.to_representation(self.instance)
        assert representation == 'http://example.org/example/1/'

    def test_representation_unsaved_object(self):
        representation = self.field.to_representation(MockObject(pk=None))
        assert representation is None

    def test_representation_with_format(self):
        self.field._context['format'] = 'xml'
        representation = self.field.to_representation(self.instance)
        assert representation == 'http://example.org/example/1.xml/'

    def test_improperly_configured(self):
        """
        If a matching view cannot be reversed with the given instance,
        the the user has misconfigured something, as the URL conf and the
        hyperlinked field do not match.
        """
        self.field.reverse = fail_reverse
        with pytest.raises(ImproperlyConfigured):
            self.field.to_representation(self.instance)


class TestHyperlinkedIdentityFieldWithFormat(APISimpleTestCase):
    """
    Tests for a hyperlinked identity field that has a `format` set,
    which enforces that alternate formats are never linked too.

    Eg. If your API includes some endpoints that accept both `.xml` and `.json`,
    but other endpoints that only accept `.json`, we allow for hyperlinked
    relationships that enforce only a single suffix type.
    """

    def setUp(self):
        self.instance = MockObject(pk=1, name='foo')
        self.field = serializers.HyperlinkedIdentityField(view_name='example', format='json')
        self.field.reverse = mock_reverse
        self.field._context = {'request': True}

    def test_representation(self):
        representation = self.field.to_representation(self.instance)
        assert representation == 'http://example.org/example/1/'

    def test_representation_with_format(self):
        self.field._context['format'] = 'xml'
        representation = self.field.to_representation(self.instance)
        assert representation == 'http://example.org/example/1.json/'


class TestSlugRelatedField(APISimpleTestCase):
    def setUp(self):
        self.queryset = MockQueryset([
            MockObject(pk=1, name='foo'),
            MockObject(pk=2, name='bar'),
            MockObject(pk=3, name='baz')
        ])
        self.instance = self.queryset.items[2]
        self.field = serializers.SlugRelatedField(
            slug_field='name', queryset=self.queryset
        )

    def test_slug_related_lookup_exists(self):
        instance = self.field.to_internal_value(self.instance.name)
        assert instance is self.instance

    def test_slug_related_lookup_does_not_exist(self):
        with pytest.raises(serializers.ValidationError) as excinfo:
            self.field.to_internal_value('doesnotexist')
        msg = excinfo.value.detail[0]
        assert msg == 'Object with name=doesnotexist does not exist.'

    def test_slug_related_lookup_invalid_type(self):
        with pytest.raises(serializers.ValidationError) as excinfo:
            self.field.to_internal_value(BadType())
        msg = excinfo.value.detail[0]
        assert msg == 'Invalid value.'

    def test_representation(self):
        representation = self.field.to_representation(self.instance)
        assert representation == self.instance.name

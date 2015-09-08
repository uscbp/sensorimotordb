from django.contrib.auth.models import User
from tastypie import fields
from tastypie.constants import ALL, ALL_WITH_RELATIONS
from tastypie.resources import ModelResource
from tastypie.authorization import Authorization
from tastypie.paginator import Paginator
from tastypie.exceptions import BadRequest
from mirrordb.models import Experiment, Unit, BrainRegion, RecordingTrial, Event, GraspObservationCondition, Species, GraspPerformanceCondition, Condition, UnitRecording, Nomenclature

from django.conf.urls import patterns, url, include
from django.http import Http404
from haystack.query import SearchQuerySet, EmptySearchQuerySet
from tastypie.utils import trailing_slash

class UserResource(ModelResource):
    class Meta:
        queryset = User.objects.all()
        resource_name = 'user'
        authorization = Authorization()


class SpeciesResource(ModelResource):
    class Meta:
        queryset = Species.objects.all()
        resource_name = 'species'
        authorization= Authorization()


class BrainRegionResource(ModelResource):
    class Meta:
        queryset = BrainRegion.objects.all()
        resource_name = 'brain_region'
        authorization= Authorization()


class NomenclatureResource(ModelResource):
    species=fields.ManyToManyField(SpeciesResource, 'species')

    class Meta:
        queryset=Nomenclature.objects.all()
        resource_name='nomenclature'
        authorization=Authorization()


class ExperimentResource(ModelResource):
    collator=fields.ForeignKey(UserResource, 'collator', full=True)
    class Meta:
        queryset = Experiment.objects.all()
        resource_name = 'experiment'
        authorization= Authorization()


class UnitResource(ModelResource):
    area = fields.ForeignKey(BrainRegionResource, 'area',full=True)

    class Meta:
        queryset = Unit.objects.all()
        resource_name = 'unit'
        authorization= Authorization()


class UnitRecordingResource(ModelResource):
    unit = fields.ForeignKey(UnitResource, 'unit', full=True)
    class Meta:
        queryset = UnitRecording.objects.all()
        resource_name = 'unit_recording'
        authorization= Authorization()
        filtering={
            'unit': ALL_WITH_RELATIONS
        }


class EventResource(ModelResource):
    class Meta:
        queryset = Event.objects.all()
        resource_name = 'event'
        authorization= Authorization()


class RecordingTrialResource(ModelResource):
    unit_recordings= fields.ToManyField(UnitRecordingResource, 'unit_recordings', full=True, null=True)
    events=fields.ToManyField(EventResource, 'events', full=True, null=True)
    class Meta:
        queryset = RecordingTrial.objects.all()
        resource_name = 'recording_trial'
        authorization= Authorization()
        filtering={
            'unit_recordings': ALL_WITH_RELATIONS
        }


class GraspPerformanceConditionResource(ModelResource):
    experiment=fields.ForeignKey(ExperimentResource, 'experiment', full=True)
    recording_trials=fields.ToManyField(RecordingTrialResource, 'recording_trials', full=True, null=True)
    class Meta:
        queryset = GraspPerformanceCondition.objects.all()
        resource_name = 'grasp_performance_condition'
        authorization= Authorization()
        filtering={
            'recording_trials': ALL_WITH_RELATIONS
        }


class GraspObservationConditionResource(ModelResource):
    demonstrator_species=fields.ForeignKey(SpeciesResource, 'demonstrator_species', full=True)
    experiment=fields.ForeignKey(ExperimentResource, 'experiment', full=True)
    recording_trials=fields.ToManyField(RecordingTrialResource, 'recording_trials', full=True, null=True)
    class Meta:
        queryset = GraspObservationCondition.objects.all()
        resource_name = 'grasp_observation_condition'
        authorization= Authorization()
        filtering={
            'recording_trials': ALL_WITH_RELATIONS
        }

    def prepend_urls(self):
        return [
            url(r"^(?P<resource_name>%s)/search/?$" % (self._meta.resource_name), self.wrap_view('get_search'), name="api_get_search"),
        ]

    def get_search(self, request, **kwargs):
        '''
        Custom endpoint for search
        '''

        self.method_check(request, allowed=['get'])
        self.is_authenticated(request)
        self.throttle_check(request)

        query = request.GET.get('demonstration_type', None)
        if not query:
            raise BadRequest('Please supply the search parameter (e.g. "/mirrordb/api/v1/grasp_observation_condition/search/?demonstration_type=css")')

        print query 
        
        results = SearchQuerySet().models(GraspObservationCondition).filter(demonstration_type=query)
        if not results:
            results = EmptySearchQuerySet()
        
        paginator = Paginator(request.GET, results, resource_uri='/mirrordb/api/v1/grasp_observation_condition/search/')

        bundles = []
        for result in paginator.page()['objects']:
            bundle = self.build_bundle(obj=result.object, request=request)
            bundles.append(self.full_dehydrate(bundle))

        object_list = {
            'meta': paginator.page()['meta'],
            'objects': bundles
        }
        object_list['meta']['search_query'] = query

        self.log_throttled_access(request)
        return self.create_response(request, object_list)

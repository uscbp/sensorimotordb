import hashlib
import random
from django.contrib.auth.models import User
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import EmailMessage
from django.db import models
import datetime
import h5py
import numpy as np

# Animal species
class Species(models.Model):
    genus_name = models.CharField(max_length=200)
    species_name = models.CharField(max_length=200)
    common_name = models.CharField(max_length=200, blank=True)

    class Meta:
        app_label='mirrordb'
        # When listing multiple records - the plural form of species is species, not speciess
        verbose_name_plural = 'species'

    # when printing instances of this class, print "genus species"
    def __unicode__(self):
        return u"%s %s" % (self.genus_name, self.species_name)


# Brain nomenclature
class Nomenclature(models.Model):
    # literature record the nomenclature is published in
    pubmed_id=models.CharField(max_length=50, blank=True)
    name = models.CharField(max_length=200)
    version = models.CharField(max_length=100)
    # species the nomenclature is based on
    species = models.ManyToManyField(Species)

    class Meta:
        app_label='mirrordb'
        # when listing multiple instances of this class, order name
        ordering=['name']

    # when printing instances of this class, print "name (version)"
    def __unicode__(self):
        return u"%s (%s)" % (self.name, self.version)

    def species_name(self):
        return ', '.join([species.__unicode__() for species in self.species.all()])


# Brain Region
class BrainRegion(models.Model):
    REGION_TYPE_CHOICES = (
        ('', ''),
        ('fiber tract', 'fiber tract'),
        ('neural region', 'neural region'),
        ('ventricle', 'ventricle'),
        )
    # nomenclature region belongs to
    nomenclature = models.ForeignKey('Nomenclature')
    name = models.CharField(max_length=100)
    abbreviation = models.CharField(max_length=50, blank=True)
    # can be a fiber tract, neural region, or ventricle
    brain_region_type = models.CharField(max_length=100, choices=REGION_TYPE_CHOICES)
    # parent brain region
    parent_region = models.ForeignKey('BrainRegion', blank=True, null=True)

    class Meta:
        app_label='mirrordb'
        # when listing multiple instances of this class, order by nomenclature then name
        ordering=['nomenclature', 'name']

    # When printing instances of this class, print "nomenclature - abbreviation" or "nomenclature - name"
    def __unicode__(self):
        if len(self.abbreviation)>0:
            return u"%s" % self.abbreviation
        else:
            return u"%s" % self.name

    def as_json(self):
        json={
            'id': self.id,
            'name': self.name,
            'abbreviation': self.abbreviation,
            'type': self.brain_region_type,
            'parent_region': '',
            'nomenclature': self.nomenclature.__unicode__(),
            'species': ','.join([species.__unicode__() for species in self.nomenclature.species.all()])
        }
        if self.parent_region is not None:
            json['parent_region']=self.parent_region.__unicode__()
        return json

    def species_name(self):
        return self.nomenclature.species_name()

    def parent_region_name(self):
        if self.parent_region is not None:
            return self.parent_region.__unicode__()
        return ''


class Experiment(models.Model):
    ##
    # A summary of neurophysiological experiment
    ##

    # user who added the entry
    collator = models.ForeignKey(User,null=True)
    title = models.CharField(max_length=200)
    brief_description = models.TextField(blank=True)
    narrative = models.TextField(blank=True)
    # date and time this entry was created
    creation_time = models.DateTimeField(auto_now_add=True,blank=True)
    # date and time this entry as last modified
    last_modified_time = models.DateTimeField(auto_now=True,blank=True)
    # user who last modified the entry
    last_modified_by = models.ForeignKey(User,null=True,blank=True,related_name='last_modified_by')
    subject_species=models.ForeignKey('Species', related_name='subject')
    pubmed_id=models.CharField(max_length=50, blank=True)

    class Meta:
        app_label='mirrordb'
        permissions=(
            ('export','Export raw data'),
            )

    def export(self, output_file):
        f = h5py.File(output_file, 'w')
        f.attrs['id']=self.id
        f.attrs['collator']=np.string_(self.collator.__unicode__())
        f.attrs['title']=np.string_(self.title)
        f.attrs['brief_description']=np.string_(self.brief_description)
        f.attrs['narrative']=np.string_(self.narrative)
        f.attrs['subject_species']=np.string_(self.subject_species.__unicode__())

        f_conditions=f.create_group('conditions')
        for condition in Condition.objects.filter(sed=self):
            f_condition=f_conditions.create_group(str(condition.id))

            if condition.type=='grasp_observe':
                condition=GraspObservationCondition.objects.get(id=condition.id)
            elif condition.type=='grasp_perform':
                condition=GraspPerformanceCondition.objects.get(id=condition.id)
            condition.export(f_condition)

        f_units=f.create_group('units')
        for unit in Unit.objects.filter(unitrecording__trial__condition__sed=self).distinct():
            f_unit=f_units.create_group(str(unit.id))
            unit.export(f_unit)

        f_trials=f.create_group('trials')
        for trial in RecordingTrial.objects.filter(condition__sed=self).distinct():
            f_trial=f_trials.create_group('condition_%d.unit_%d.trial_%d' % (trial.condition.id, trial.unit.id,
                                                                             trial.trial_number))
            trial.export(f_trial)

        f.close()


class Condition(models.Model):
    experiment=models.ForeignKey('Experiment')
    name=models.CharField(max_length=100)
    description=models.TextField()
    type=models.CharField(max_length=50)

    class Meta:
        app_label='mirrordb'

    def export(self, group):
        group.attrs['id']=self.id
        group.attrs['name']=np.string_(self.name)
        group.attrs['description']=np.string_(self.description)
        group.attrs['type']=np.string_(self.type)


class GraspCondition(Condition):
    object=models.CharField(max_length=50)
    object_distance=models.DecimalField(max_digits=6, decimal_places=3)
    grasp=models.CharField(max_length=50)

    class Meta:
        app_label='mirrordb'

    def export(self, group):
        super(GraspCondition,self).export(group)
        group.attrs['object']=np.string_(self.object)
        group.attrs['object_distance']=float(self.object_distance)
        group.attrs['grasp']=np.string_(self.grasp)


class GraspPerformanceCondition(GraspCondition):
    hand_visible = models.BooleanField()
    object_visible = models.BooleanField()

    class Meta:
        app_label='mirrordb'

    def export(self, group):
        super(GraspPerformanceCondition,self).export(group)

        group.attrs['hand_visible']=self.hand_visible
        group.attrs['object_visible']=self.object_visible


class GraspObservationCondition(GraspCondition):
    DEMONSTRATION_CHOICES=(
        ('live','live'),
        ('video','video')
        )
    demonstrator_species=models.ForeignKey('Species', related_name='demonstrator')
    demonstration_type=models.CharField(max_length=30, choices=DEMONSTRATION_CHOICES)
    viewing_angle=models.DecimalField(max_digits=6, decimal_places=3)
    whole_body_visible = models.BooleanField()

    class Meta:
        app_label='mirrordb'

    def export(self, group):
        super(GraspObservationCondition,self).export(group)

        group.attrs['demonstrator_species']=np.string_(self.demonstrator_species.__unicode__())
        group.attrs['demonstration_type']=np.string_(self.demonstration_type)
        group.attrs['viewing_angle']=float(self.viewing_angle)
        group.attrs['whole_body_visible']=self.whole_body_visible


class Unit(models.Model):
    type=models.CharField(max_length=50)
    area=models.ForeignKey('BrainRegion')

    class Meta:
        app_label='mirrordb'

    def export(self, group):
        group.attrs['id']=self.id
        group.attrs['type']=np.string_(self.type)
        group.attrs['area']=np.string_(self.area.__unicode__())


class RecordingTrial(models.Model):
    condition=models.ForeignKey('Condition',null=True,related_name='recording_trials')
    trial_number=models.IntegerField()
    start_time=models.DecimalField(max_digits=10, decimal_places=5)
    end_time=models.DecimalField(max_digits=10, decimal_places=5)

    class Meta:
        app_label='mirrordb'

    def export(self, group):
        group.attrs['trial_number']=self.trial_number
        group.attrs['condition']=self.condition.id
        group.attrs['start_time']=float(self.start_time)
        group.attrs['end_time']=float(self.end_time)
        f_events=group.create_group('events')
        for event in Event.objects.filter(trial=self):
            f_event=f_events.create_group(event.name)
            f_event.attrs['description']=np.string_(event.description)
            f_event.attrs['time']=float(event.time)
        f_units=group.create_group('unit_recordings')
        for unit_recording in UnitRecording.objects.filter(trial=self):
            f_unit_recording=f_units.create_group('unit_%d' % unit_recording.unit.id)
            unit_recording.export(f_unit_recording)


class UnitRecording(models.Model):
    trial=models.ForeignKey('RecordingTrial', related_name='unit_recordings')
    unit=models.ForeignKey('Unit')
    spike_times=models.TextField()

    class Meta:
        app_label='mirrordb'

    def __init__(self, *args, **kwargs):
        super(UnitRecording,self).__init__(*args, **kwargs)
        spikes=self.spike_times.split(',')
        self.spike_times_array=np.zeros(len(spikes))
        for idx,spike in enumerate(spikes):
            if len(spike) and float(spike)>=float(self.trial.start_time)-1.0 and float(spike)<float(self.trial.end_time)+1.0:
                self.spike_times_array[idx]=float(spike)

    def export(self, group):
        group.attrs['unit']=self.unit.id
        group['spike_times']=self.spike_times_array


class Event(models.Model):
    trial=models.ForeignKey('RecordingTrial', related_name='events')
    name=models.CharField(max_length=100)
    description=models.TextField()
    time=models.DecimalField(max_digits=10, decimal_places=5)

    class Meta:
        app_label='mirrordb'


class ExperimentExportRequest(models.Model):
    STATUS_OPTIONS=(
        ('',''),
        ('accepted','accepted'),
        ('declined','declined')
        )
    experiment=models.ForeignKey('Experiment')
    requesting_user=models.ForeignKey(User, related_name='requesting_user')
    request_body=models.CharField(max_length=1000, blank=False)
    status=models.CharField(max_length=20, choices=STATUS_OPTIONS, blank=True)
    activation_key = models.CharField('activation key', max_length=40)
    sent=models.DateTimeField(auto_now=True, blank=True)

    class Meta:
        app_label='mirrordb'

    def send(self):
        # message subject
        subject = 'Request to export neurophysiology data'
        # message text
        text = 'You\'ve been sent a request by %s to export data from the Neurophysiology Experiment: %s.<br>' % (
            self.requesting_user, self.experiment.__unicode__())
        text += self.request_body
        text += '<br>Click one of the following links to accept or decline the request:<br>'
        accept_url = ''.join(
            ['http://', get_current_site(None).domain, '/mirrordb/experiment/export_request/accept/%s/' % self.activation_key])
        decline_url = ''.join(
            ['http://', get_current_site(None).domain, '/mirrordb/experiment/export_request/decline/%s/' % self.activation_key])
        text += '<a href="%s">Accept</a><br>' % accept_url
        text += 'or<br>'
        text += '<a href="%s">Decline</a>' % decline_url
        self.sent=datetime.datetime.now()
        msg = EmailMessage(subject, text, 'uscbrainproject@gmail.com', [self.sed.collator.email])
        msg.content_subtype = "html"  # Main content is now text/html
        msg.send(fail_silently=True)

    def save(self, **kwargs):
        if self.id is None:
            salt = hashlib.sha1(str(random.random())).hexdigest()[:5]
            username = self.requesting_user.username
            if isinstance(username, unicode):
                username = username.encode('utf-8')
            self.activation_key = hashlib.sha1(salt+username).hexdigest()

            self.send()
        super(ExperimentExportRequest,self).save(**kwargs)



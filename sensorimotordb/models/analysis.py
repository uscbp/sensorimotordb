from django.db import models
from model_utils.managers import InheritanceManager
from mptt.fields import TreeForeignKey
from mptt.models import MPTTModel
import numpy as np
import os
from rpy2 import robjects
from sensorimotordb.models import UnitRecording, Condition, Unit, RecordingTrial, Event
from uscbp import settings
from rpy2.robjects import pandas2ri
pandas2ri.activate()
import pandas as pd


class Analysis(models.Model):
    name=models.CharField(max_length=100, blank=False)
    description=models.TextField()

    objects = InheritanceManager()
    class Meta:
        app_label='sensorimotordb'

    def run(self, results):
        pass

class AnalysisResults(models.Model):
    analysis = models.ForeignKey('Analysis')
    experiment = models.ForeignKey('Experiment')
    name=models.CharField(max_length=100, blank=False)
    description=models.TextField()
    date_run=models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label='sensorimotordb'


class UnitAnalysisResults(models.Model):
    analysis_results=models.ForeignKey('AnalysisResults', related_name='unit_analysis_results')
    unit=models.ForeignKey('Unit')
    results_text=models.TextField()

    class Meta:
        app_label='sensorimotordb'


class Factor(models.Model):
    analysis=models.ForeignKey('Analysis', related_name='factors')
    name=models.CharField(max_length=1000, blank=False)

    class Meta:
        app_label='sensorimotordb'


class Level(models.Model):
    factor=models.ForeignKey('Factor', related_name='levels')
    value=models.CharField(max_length=1000, blank=False)

    class Meta:
        app_label='sensorimotordb'


class AnalysisResultsLevelMapping(models.Model):
    level=models.ForeignKey('Level')
    analysis_results=models.ForeignKey(AnalysisResults, related_name='level_mappings')
    conditions=models.ManyToManyField(Condition)

    class Meta:
        app_label='sensorimotordb'


class UnitClassification(MPTTModel,models.Model):
    # parent BOP
    parent = TreeForeignKey('self', null=True, blank=True, related_name='children')
    analysis_results=models.ForeignKey(AnalysisResults, related_name='unit_classifications')
    label=models.CharField(max_length=1000, blank=False)
    units=models.ManyToManyField(Unit)

    class Meta:
        app_label='sensorimotordb'


def get_woi_spikes(unit_recording, trial_start_time, trial_events, rel_evt, rel_start_ms, rel_end_ms, rel_end_evt):
    if len(rel_end_evt) == 0:
        woi_time_zero = float(trial_start_time)
        if not rel_evt == 'start':
            if trial_events.filter(name=rel_evt).exists():
                woi_evt = trial_events.get(name=rel_evt)
                woi_time_zero = float(woi_evt.time)
            else:
                return None
        woi_spikes = unit_recording.get_spikes_relative(woi_time_zero, [rel_start_ms, rel_end_ms])
    else:
        if trial_events.filter(name=rel_evt).exists() and trial_events.filter(name=rel_end_evt).exists():
            woi_time_start = float(trial_start_time)
            if not rel_evt == 'start':
                woi_start_evt = trial_events.get(name=rel_evt)
                woi_time_start = float(woi_start_evt.time)
            woi_time_end = float(unit_recording.trial.start_time)
            if not rel_end_evt == 'start':
                woi_end_evt = trial_events.get(name=rel_end_evt)
                woi_time_end = float(woi_end_evt.time)
            woi_spikes = unit_recording.get_spikes_fixed([woi_time_start, woi_time_end])
        else:
            return None
    return woi_spikes

def get_woi_firing_rate(unit_recording, trial_start_time, trial_events, rel_evt, rel_start_ms, rel_end_ms, rel_end_evt):
    rate=None
    if len(rel_end_evt) == 0:
        woi_time_zero = trial_start_time
        found=True
        if not rel_evt == 'start':
            found=False
            for trial_evt in trial_events:
                if trial_evt.name==rel_evt:
                    woi_time_zero = float(trial_evt.time)
                    found=True
                    break
        if found:
            woi_spikes = unit_recording.get_spikes_relative(woi_time_zero, [rel_start_ms, rel_end_ms])
            rate=len(woi_spikes)/(rel_end_ms-rel_start_ms)
    else:
        try:
            woi_time_start = trial_start_time
            found_start=True
            if not rel_evt == 'start':
                found_start=False
                for trial_evt in trial_events:
                    if trial_evt.name==rel_evt:
                        woi_time_start = float(trial_evt.time)
                        found_start=True
                        break
            woi_time_end = trial_start_time
            found_end=True
            if not rel_end_evt == 'start':
                found_end=False
                for trial_evt in trial_events:
                    if trial_evt.name==rel_end_evt:
                        woi_time_end = float(trial_evt.time)
                        found_end=True
                        break
            if found_start and found_end:
                woi_spikes = unit_recording.get_spikes_fixed([woi_time_start, woi_time_end])
                rate=len(woi_spikes)/(woi_time_end-woi_time_start)
        except:
            print('Exception')
            return None
    return rate


class VisuomotorClassificationAnalysisResults(AnalysisResults):
    baseline_rel_evt=models.CharField(max_length=1000, blank=False)
    baseline_rel_start=models.IntegerField(blank=True, null=True)
    baseline_rel_end=models.IntegerField(blank=True, null=True)
    baseline_rel_end_evt=models.CharField(max_length=1000, blank=True, null=True)
    obj_view_woi_rel_evt=models.CharField(max_length=1000, blank=False)
    obj_view_woi_rel_start=models.IntegerField(blank=True, null=True)
    obj_view_woi_rel_end=models.IntegerField(blank=True, null=True)
    obj_view_woi_rel_end_evt=models.CharField(max_length=1000, blank=True, null=True)
    grasp_woi_rel_evt=models.CharField(max_length=1000, blank=False)
    grasp_woi_rel_start=models.IntegerField(blank=True, null=True)
    grasp_woi_rel_end=models.IntegerField(blank=True, null=True)
    grasp_woi_rel_end_evt=models.CharField(max_length=1000, blank=True, null=True)
    total_num_units=models.IntegerField(blank=True, null=True)

    class Meta:
        app_label='sensorimotordb'


class VisuomotorClassificationUnitAnalysisResults(UnitAnalysisResults):
    pairwise_results_text=models.TextField()

    class Meta:
        app_label='sensorimotordb'


class VisuomotorClassificationAnalysis(Analysis):

    class Meta:
        app_label='sensorimotordb'

    def run(self, results):
        unit_ids=np.unique(UnitRecording.objects.filter(trial__condition__experiment=results.experiment).values_list('unit',
            flat=True))
        results.total_num_units=len(unit_ids)
        results.save()

        unit_classifications={
            "motor":UnitClassification(analysis_results=results, label='motor'),
            "visual":UnitClassification(analysis_results=results, label='visual'),
            "visuomotor":UnitClassification(analysis_results=results, label='visuomotor'),
            "other":UnitClassification(analysis_results=results, label='other')
        }
        for label, classification in unit_classifications.iteritems():
            classification.save()
        unit_classifications['canonical']=UnitClassification(parent=unit_classifications['visuomotor'],analysis_results=results,label='canonical')
        unit_classifications['canonical'].save()
        unit_classifications['mirror']=UnitClassification(parent=unit_classifications['visuomotor'],analysis_results=results,label='mirror')
        unit_classifications['mirror'].save()
        unit_classifications['canonical mirror']=UnitClassification(parent=unit_classifications['visuomotor'],analysis_results=results,label='canonical mirror')
        unit_classifications['canonical mirror'].save()
        unit_classifications['motor - ringhook']=UnitClassification(parent=unit_classifications['motor'],analysis_results=results,label='ringhook')
        unit_classifications['motor - ringhook'].save()
        unit_classifications['motor - smallconeside']=UnitClassification(parent=unit_classifications['motor'],analysis_results=results,label='smallconeside')
        unit_classifications['motor - smallconeside'].save()
        unit_classifications['motor - largeconewhole']=UnitClassification(parent=unit_classifications['motor'],analysis_results=results,label='largeconewhole')
        unit_classifications['motor - largeconewhole'].save()
        unit_classifications['visual - ringhook']=UnitClassification(parent=unit_classifications['visual'],analysis_results=results,label='ringhook')
        unit_classifications['visual - ringhook'].save()
        unit_classifications['visual - smallconeside']=UnitClassification(parent=unit_classifications['visual'],analysis_results=results,label='smallconeside')
        unit_classifications['visual - smallconeside'].save()
        unit_classifications['visual - largeconewhole']=UnitClassification(parent=unit_classifications['visual'],analysis_results=results,label='largeconewhole')
        unit_classifications['visual - largeconewhole'].save()

        for unit_id in unit_ids:
            unit=Unit.objects.get(id=unit_id)
            (motor_anova_results,motor_pairwise)=self.test_unit_motor(results, unit)
            print(motor_anova_results)
            print(motor_pairwise)
            (objpres_anova_results,objpres_trialtype_pairwise,objpres_objectgrasp_pairwise,
                objpres_trialtypeobjectgrasp_pairwise,objpres_objectgrasptrialtype_pairwise, objpres_pref)=self.test_unit_obj_pres(results, unit)
            (obs_grasp_anova_results,obs_grasp_objectgrasp_pairwise)=self.test_unit_obs_grasp(results, unit)

            unit_results=VisuomotorClassificationUnitAnalysisResults(analysis_results=results,
                results_text='\n'.join(['<h2>Motor</h2>',str(motor_anova_results),
                                        '<h2>Object Presentation</h2>',str(objpres_anova_results),
                                        '<h2>Observation - Object Grasp</h2>',str(obs_grasp_anova_results)]),
                pairwise_results_text='\n'.join(['<h2>Motor</h2>',
                                                 str(motor_visibility_pairwise),
                                                 str(motor_objectgrasp_pairwise),
                                                 str(motor_visibilityobjectgrasp_pairwise),
                                                 str(motor_objectgraspvisibility_pairwise),
                                                 '<h2>Object Presentation</h2>',
                                                 str(objpres_trialtype_pairwise),
                                                 str(objpres_objectgrasp_pairwise),
                                                 str(objpres_trialtypeobjectgrasp_pairwise),
                                                 str(objpres_objectgrasptrialtype_pairwise),
                                                 '<h2>Observation - Object Grasp</h2>',
                                                 str(obs_grasp_objectgrasp_pairwise)]),
                unit=unit)
            unit_results.save()


            # Visibility not significant (fires during grasping in light and dark)
            # Significant object/grasp (doesn't fire for all types of grasps)
            motor_properties=motor_anova_results['Pr(>F)']['visibility']>=0.05 and motor_anova_results['Pr(>F)']['visibility:objectgrasp']>=0.05 and motor_anova_results['Pr(>F)']['objectgrasp']<0.05

            # Trial type not significant (fires during go and no/go)
            # Significant object/grasp (doesn't fire for all types of objects)
            obj_pres=objpres_anova_results['Pr(>F)']['trial_type']>=0.05 and objpres_anova_results['Pr(>F)']['objectgrasp']<0.05

            # Significant object/grasp (doesn't fire during observation of all grasp types)
            action_obs=obs_grasp_anova_results['Pr(>F)']['objectgrasp']<0.05

            # If cell has motor and visual properties -> visomotor
            if motor_properties and (obj_pres or action_obs):
                unit_classifications['visuomotor'].units.add(Unit.objects.get(id=unit_id))
                # If fires for object presentation and action observation -> canonical mirror
                if obj_pres and action_obs:
                    unit_classifications['canonical mirror'].units.add(Unit.objects.get(id=unit_id))
                # If fires only for object presentation -> canonical
                elif obj_pres:
                    unit_classifications['canonical'].units.add(Unit.objects.get(id=unit_id))
                # If fires only during action observation -> mirror
                else:
                    unit_classifications['mirror'].units.add(Unit.objects.get(id=unit_id))
            # If only has motor properties -> motor
            elif motor_properties :
                unit_classifications['motor'].units.add(Unit.objects.get(id=unit_id))
                if len(motor_pref):
                    unit_classifications['motor - %s' % motor_pref].units.add(Unit.objects.get(id=unit_id))
            # If only has visual properties -> visual
            elif obj_pres or action_obs:
                unit_classifications['visual'].units.add(Unit.objects.get(id=unit_id))
                if len(objpres_pref):
                    unit_classifications['visual - %s' % objpres_pref].units.add(Unit.objects.get(id=unit_id))
            # Otherwise other
            else:
                unit_classifications['other'].units.add(Unit.objects.get(id=unit_id))

        print('%.4f %% motor cells' % (unit_classifications['motor'].units.count()/float(len(unit_ids))*100.0))
        print('%.4f %% visual cells' % (unit_classifications['visual'].units.count()/float(len(unit_ids))*100.0))
        print('%.4f %% visuomotor cells' % (unit_classifications['visuomotor'].units.count()/float(len(unit_ids))*100.0))
        print('%.4f %% other cells' % (unit_classifications['other'].units.count()/float(len(unit_ids))*100.0))


    def test_unit_motor(self, results, unit):
        trial_ids=[]
        visibilities=[]
        objectgrasps=[]
        epochs=[]
        rates=[]
        condition_ids=[]
        for factor_name in ['Grasp Execution: Visibility','Grasp Execution: Object/Grasp']:
            factor=Factor.objects.get(analysis=results.analysis, name=factor_name)
            for level in factor.levels.all():
                conditions=AnalysisResultsLevelMapping.objects.get(level=level,analysis_results=results).conditions.all()
                for condition in conditions:
                    if not condition.id in condition_ids:
                        condition_ids.append(condition.id)
        conditions=Condition.objects.filter(id__in=condition_ids)
        for condition in conditions:
            recording_trials=RecordingTrial.objects.filter(condition=condition)
            for trial in recording_trials:
                trial_events=list(Event.objects.filter(trial=trial))
                trial_start_time=float(trial.start_time)
                if UnitRecording.objects.filter(trial=trial, unit=unit).count():
                    unit_recording=UnitRecording.objects.get(trial=trial, unit=unit)

                    baseline_rel_start=0
                    if results.baseline_rel_start is not None:
                        baseline_rel_start=results.baseline_rel_start/1000.0
                    baseline_rel_end=0
                    if results.baseline_rel_end is not None:
                        baseline_rel_end=results.baseline_rel_end/1000.0
                    baseline_rate = get_woi_firing_rate(unit_recording, trial_start_time, trial_events, results.baseline_rel_evt,
                        baseline_rel_start, baseline_rel_end, results.baseline_rel_end_evt)

                    grasp_woi_rel_start=0
                    if results.grasp_woi_rel_start is not None:
                        grasp_woi_rel_start=results.grasp_woi_rel_start/1000.0
                    grasp_woi_rel_end=0
                    if results.grasp_woi_rel_end is not None:
                        grasp_woi_rel_end=results.grasp_woi_rel_end/1000.0
                    woi_rate = get_woi_firing_rate(unit_recording, trial_start_time, trial_events, results.grasp_woi_rel_evt,
                        grasp_woi_rel_start, grasp_woi_rel_end, results.grasp_woi_rel_end_evt)

                    if baseline_rate is not None and woi_rate is not None:
                        visibility=Level.objects.get(factor__analysis=self,factor__name='Grasp Execution: Visibility',
                            analysisresultslevelmapping__conditions=condition,
                            analysisresultslevelmapping__analysis_results=results).value
                        objectgrasp=Level.objects.get(factor__analysis=self,factor__name='Grasp Execution: Object/Grasp',
                            analysisresultslevelmapping__conditions=condition,
                            analysisresultslevelmapping__analysis_results=results).value

                        trial_ids.append(trial.id)
                        visibilities.append(visibility)
                        objectgrasps.append(objectgrasp)
                        epochs.append('baseline')
                        rates.append(baseline_rate)

                        trial_ids.append(trial.id)
                        visibilities.append(visibility)
                        objectgrasps.append(objectgrasp)
                        epochs.append('grasping')
                        rates.append(woi_rate)


        df= pd.DataFrame({
            'trial': pd.Series(trial_ids),
            'visibility': pd.Series(visibilities),
            'objectgrasp': pd.Series(objectgrasps),
            'epoch': pd.Series(epochs),
            'rate': pd.Series(rates)
        })

        df=df.set_index(['trial'])

        r_source = robjects.r['source']
        r_source(os.path.join(settings.PROJECT_PATH,'../sensorimotordb/analysis/three_way_anova_repeated_measures.R'))
        r_three_way_anova = robjects.globalenv['three_way_anova_repeated_measures']
        (anova_results, pairwise)=r_three_way_anova(df,"trial","rate","epoch","objectgrasp","visibility")
        anova_results=pandas2ri.ri2py_dataframe(anova_results)
        pairwise=pandas2ri.ri2py_dataframe(pairwise)

        return anova_results,pairwise


    def test_unit_obj_pres(self, results, unit):
        trial_ids=[]
        trial_types=[]
        objectgrasps=[]
        rate_diff=[]
        condition_ids=[]
        objectgrasps_rates={}
        for factor_name in ['Object Presentation - Trial Type','Object Presentation - Object']:
            factor=Factor.objects.get(analysis=results.analysis, name=factor_name)
            for level in factor.levels.all():
                conditions=AnalysisResultsLevelMapping.objects.get(level=level,analysis_results=results).conditions.all()
                for condition in conditions:
                    if not condition.id in condition_ids:
                        condition_ids.append(condition.id)
        conditions=Condition.objects.filter(id__in=condition_ids)
        for condition in conditions:
            recording_trials=RecordingTrial.objects.filter(condition=condition)
            for trial in recording_trials:
                trial_events=list(Event.objects.filter(trial=trial))
                trial_start_time=float(trial.start_time)
                if UnitRecording.objects.filter(trial=trial, unit=unit).count():
                    unit_recording=UnitRecording.objects.get(trial=trial, unit=unit)

                    baseline_rel_start=0
                    if results.baseline_rel_start is not None:
                        baseline_rel_start=results.baseline_rel_start/1000.0
                    baseline_rel_end=0
                    if results.baseline_rel_end is not None:
                        baseline_rel_end=results.baseline_rel_end/1000.0
                    baseline_rate = get_woi_firing_rate(unit_recording, trial_start_time, trial_events, results.baseline_rel_evt,
                        baseline_rel_start, baseline_rel_end, results.baseline_rel_end_evt)

                    obj_view_woi_rel_start=0
                    if results.obj_view_woi_rel_start is not None:
                        obj_view_woi_rel_start=results.obj_view_woi_rel_start/1000.0
                    obj_view_woi_rel_end=0
                    if results.obj_view_woi_rel_end is not None:
                        obj_view_woi_rel_end=results.obj_view_woi_rel_end/1000.0
                    woi_rate = get_woi_firing_rate(unit_recording, trial_start_time, trial_events, results.obj_view_woi_rel_evt,
                        obj_view_woi_rel_start, obj_view_woi_rel_end, results.obj_view_woi_rel_end_evt)

                    if baseline_rate is not None and woi_rate is not None:
                        trial_type=Level.objects.get(factor__analysis=self,factor__name='Object Presentation - Trial Type',
                            analysisresultslevelmapping__conditions=condition,
                            analysisresultslevelmapping__analysis_results=results).value
                        objectgrasp=Level.objects.get(factor__analysis=self,factor__name='Object Presentation - Object',
                            analysisresultslevelmapping__conditions=condition,
                            analysisresultslevelmapping__analysis_results=results).value

                        trial_ids.append(trial.id)
                        trial_types.append(trial_type)
                        objectgrasps.append(objectgrasp)
                        rate_diff.append(woi_rate-baseline_rate)

                        if not objectgrasp in objectgrasps_rates:
                            objectgrasps_rates[objectgrasp]=[]
                        objectgrasps_rates[objectgrasp].append(woi_rate-baseline_rate)

        df= pd.DataFrame({
            'trial': pd.Series(trial_ids),
            'trial_type': pd.Series(trial_types),
            'objectgrasp': pd.Series(objectgrasps),
            'rate_diff': pd.Series(rate_diff)
        })

        df=df.set_index(['trial'])

        r_source = robjects.r['source']
        r_source(os.path.join(settings.PROJECT_PATH,'../sensorimotordb/analysis/two_way_anova.R'))
        r_two_way_anova = robjects.globalenv['two_way_anova']
        (anova_results,trialtype_pairwise,objectgrasp_pairwise,trialtypeobjectgrasp_pairwise,objectgrasptrialtype_pairwise)=r_two_way_anova(df,"rate_diff",
            "trial_type","objectgrasp")

        anova_results=pandas2ri.ri2py_dataframe(anova_results)
        trialtype_pairwise=pandas2ri.ri2py_listvector(trialtype_pairwise)
        objectgrasp_pairwise=pandas2ri.ri2py_listvector(objectgrasp_pairwise)
        trialtypeobjectgrasp_pairwise=pandas2ri.ri2py_dataframe(trialtypeobjectgrasp_pairwise)
        objectgrasptrialtype_pairwise=pandas2ri.ri2py_dataframe(objectgrasptrialtype_pairwise)

        max_rate=0
        pref_objgrasp=''
        for objgrasp in objectgrasps_rates:
            mean_rate=np.mean(objectgrasps_rates[objgrasp])
            if mean_rate>max_rate:
                max_rate=mean_rate
                pref_objgrasp=objgrasp

        return anova_results,trialtype_pairwise,objectgrasp_pairwise,trialtypeobjectgrasp_pairwise,objectgrasptrialtype_pairwise,pref_objgrasp


    def test_unit_obs_grasp(self, results, unit):
        trial_ids=[]
        objectgrasps=[]
        rate_diff=[]
        condition_ids=[]
        for factor_name in ['Grasp Observation: Object/Grasp']:
            factor=Factor.objects.get(analysis=results.analysis, name=factor_name)
            for level in factor.levels.all():
                conditions=AnalysisResultsLevelMapping.objects.get(level=level,analysis_results=results).conditions.all()
                for condition in conditions:
                    if not condition.id in condition_ids:
                        condition_ids.append(condition.id)
        conditions=Condition.objects.filter(id__in=condition_ids)
        for condition in conditions:
            recording_trials=RecordingTrial.objects.filter(condition=condition)
            for trial in recording_trials:
                trial_events=list(Event.objects.filter(trial=trial))
                trial_start_time=float(trial.start_time)
                if UnitRecording.objects.filter(trial=trial, unit=unit).count():
                    unit_recording=UnitRecording.objects.get(trial=trial, unit=unit)

                    baseline_rel_start=0
                    if results.baseline_rel_start is not None:
                        baseline_rel_start=results.baseline_rel_start/1000.0
                    baseline_rel_end=0
                    if results.baseline_rel_end is not None:
                        baseline_rel_end=results.baseline_rel_end/1000.0
                    baseline_rate = get_woi_firing_rate(unit_recording, trial_start_time, trial_events, results.baseline_rel_evt,
                        baseline_rel_start, baseline_rel_end, results.baseline_rel_end_evt)

                    grasp_woi_rel_start=0
                    if results.grasp_woi_rel_start is not None:
                        grasp_woi_rel_start=results.grasp_woi_rel_start/1000.0
                    grasp_woi_rel_end=0
                    if results.grasp_woi_rel_end is not None:
                        grasp_woi_rel_end=results.grasp_woi_rel_end/1000.0
                    woi_rate = get_woi_firing_rate(unit_recording, trial_start_time, trial_events, results.grasp_woi_rel_evt,
                        grasp_woi_rel_start, grasp_woi_rel_end, results.grasp_woi_rel_end_evt)

                    if baseline_rate is not None and woi_rate is not None:
                        objectgrasp=Level.objects.get(factor__analysis=self,factor__name='Grasp Observation: Object/Grasp',
                            analysisresultslevelmapping__conditions=condition,
                            analysisresultslevelmapping__analysis_results=results).value

                        trial_ids.append(trial.id)
                        objectgrasps.append(objectgrasp)
                        rate_diff.append(woi_rate-baseline_rate)

        df= pd.DataFrame({
            'trial': pd.Series(trial_ids),
            'objectgrasp': pd.Series(objectgrasps),
            'rate_diff': pd.Series(rate_diff)
        })

        df=df.set_index(['trial'])

        r_source = robjects.r['source']
        r_source(os.path.join(settings.PROJECT_PATH,'../sensorimotordb/analysis/one_way_anova.R'))
        r_one_way_anova = robjects.globalenv['one_way_anova']
        (anova_results,objectgrasp_pairwise)=r_one_way_anova(df,"rate_diff","objectgrasp")

        anova_results=pandas2ri.ri2py_dataframe(anova_results)
        objectgrasp_pairwise=pandas2ri.ri2py_dataframe(objectgrasp_pairwise)

        return anova_results,objectgrasp_pairwise


class MirrorTypeClassificationAnalysisResults(AnalysisResults):
    baseline_rel_evt=models.CharField(max_length=1000, blank=False)
    baseline_rel_start=models.IntegerField(blank=True, null=True)
    baseline_rel_end=models.IntegerField(blank=True, null=True)
    baseline_rel_end_evt=models.CharField(max_length=1000, blank=True, null=True)
    reach_woi_rel_evt=models.CharField(max_length=1000, blank=False)
    reach_woi_rel_start=models.IntegerField(blank=True, null=True)
    reach_woi_rel_end=models.IntegerField(blank=True, null=True)
    reach_woi_rel_end_evt=models.CharField(max_length=1000, blank=True, null=True)
    hold_woi_rel_evt=models.CharField(max_length=1000, blank=False)
    hold_woi_rel_start=models.IntegerField(blank=True, null=True)
    hold_woi_rel_end=models.IntegerField(blank=True, null=True)
    hold_woi_rel_end_evt=models.CharField(max_length=1000, blank=True, null=True)
    total_num_units=models.IntegerField(blank=True, null=True)

    class Meta:
        app_label='sensorimotordb'


class MirrorTypeClassificationUnitAnalysisResults(UnitAnalysisResults):
    pairwise_results_text=models.TextField()

    class Meta:
        app_label='sensorimotordb'


class MirrorTypeClassificationAnalysis(Analysis):

    class Meta:
        app_label='sensorimotordb'

    def run(self, results):
        unit_ids=np.unique(UnitRecording.objects.filter(trial__condition__experiment=results.experiment).values_list('unit',
            flat=True))
        results.total_num_units=len(unit_ids)
        results.save()

        unit_classifications={
            'F-F':UnitClassification(analysis_results=results, label='F-F'),
            'F-S':UnitClassification(analysis_results=results, label='F-S'),
            'F-ns':UnitClassification(analysis_results=results, label='F-ns'),
            'S-F':UnitClassification(analysis_results=results, label='S-F'),
            'S-S':UnitClassification(analysis_results=results, label='S-S'),
            'S-ns':UnitClassification(analysis_results=results, label='S-ns'),
            'ns-F':UnitClassification(analysis_results=results, label='ns-F'),
            'ns-S':UnitClassification(analysis_results=results, label='ns-S'),
            'ns-ns':UnitClassification(analysis_results=results, label='ns-ns')
        }
        for label, classification in unit_classifications.iteritems():
            classification.save()

        r_source = robjects.r['source']
        r_source(os.path.join(settings.PROJECT_PATH,'../sensorimotordb/analysis/one_way_anova_repeated_measures.R'))
        r_one_way_anova = robjects.globalenv['one_way_anova_repeated_measures']

        for unit_id in unit_ids:
            print('testing %d' % unit_id)
            unit=Unit.objects.get(id=unit_id)
            (exe_anova_results,exe_pairwise,exe_rates)=self.test_unit(r_one_way_anova, results, unit, 'execution')
            (obs_anova_results,obs_pairwise,obs_rates)=self.test_unit(r_one_way_anova, results, unit, 'observation')

            unit_results=VisuomotorClassificationUnitAnalysisResults(analysis_results=results,
                results_text='\n'.join(['<h2>Execution</h2>',str(exe_anova_results),
                                        '<h2>Observation</h2>',str(obs_anova_results)]),
                pairwise_results_text='\n'.join(['<h2>Execution</h2>',
                                                 str(exe_pairwise),
                                                 '<h2>Observation</h2>',
                                                 str(obs_pairwise)]),
                unit=unit)
            unit_results.save()

            exe_classification='ns'
            exe_anova_results=pandas2ri.ri2py_dataframe(exe_anova_results[1])
            if exe_anova_results[4][0][0]<0.05:
                # Reach compared to baseline
                if exe_pairwise[1]<0.05:
                    if np.mean(exe_rates['reach'])>np.mean(exe_rates['baseline']):
                        exe_classification='F'
                    else:
                        exe_classification='S'
                # Hold compared to baseline
                elif exe_pairwise[0]<0.05:
                    if np.mean(exe_rates['hold'])>np.mean(exe_rates['baseline']):
                        exe_classification='F'
                    else:
                        exe_classification='S'
            obs_classification='ns'
            obs_anova_results=pandas2ri.ri2py_dataframe(obs_anova_results[1])
            if obs_anova_results[4][0][0]<0.05:
                if obs_pairwise[1]<0.05:
                    if np.mean(obs_rates['reach'])>np.mean(obs_rates['baseline']):
                        obs_classification='F'
                    else:
                        obs_classification='S'
                elif obs_pairwise[0]<0.05:
                    if np.mean(obs_rates['hold'])>np.mean(exe_rates['baseline']):
                        obs_classification='F'
                    else:
                        obs_classification='S'
            unit_classifications['%s-%s' % (exe_classification,obs_classification)].units.add(Unit.objects.get(id=unit_id))

        print('%.4f %% F-F cells' % (unit_classifications['F-F'].units.count()/float(len(unit_ids))*100.0))
        print('%.4f %% F-S cells' % (unit_classifications['F-S'].units.count()/float(len(unit_ids))*100.0))
        print('%.4f %% F-ns cells' % (unit_classifications['F-ns'].units.count()/float(len(unit_ids))*100.0))
        print('%.4f %% S-F cells' % (unit_classifications['S-F'].units.count()/float(len(unit_ids))*100.0))
        print('%.4f %% S-S cells' % (unit_classifications['S-S'].units.count()/float(len(unit_ids))*100.0))
        print('%.4f %% S-ns cells' % (unit_classifications['S-ns'].units.count()/float(len(unit_ids))*100.0))
        print('%.4f %% ns-F cells' % (unit_classifications['ns-F'].units.count()/float(len(unit_ids))*100.0))
        print('%.4f %% ns-S cells' % (unit_classifications['ns-S'].units.count()/float(len(unit_ids))*100.0))
        print('%.4f %% ns-ns cells' % (unit_classifications['ns-ns'].units.count()/float(len(unit_ids))*100.0))

    def test_unit(self, r_one_way_anova, results, unit, trial_type):
        trial_ids=[]
        rates=[]
        wois=[]
        all_rates={
            'baseline':[],
            'reach':[],
            'hold':[]
        }

        condition_ids=[]
        factor=Factor.objects.get(analysis=results.analysis, name='Trial type')
        level=Level.objects.get(factor=factor, value=trial_type)
        conditions=AnalysisResultsLevelMapping.objects.get(level=level,analysis_results=results).conditions.all()
        for condition in conditions:
            if not condition.id in condition_ids:
                condition_ids.append(condition.id)

        unit_recordings=UnitRecording.objects.filter(trial__condition__id__in=condition_ids, unit=unit).select_related('trial')
        for trial_idx,unit_recording in enumerate(unit_recordings):
            trial_events=list(Event.objects.filter(trial=unit_recording.trial))
            trial_start_time=float(unit_recording.trial.start_time)

            baseline_rel_start=0
            if results.baseline_rel_start is not None:
                baseline_rel_start=results.baseline_rel_start/1000.0
            baseline_rel_end=0
            if results.baseline_rel_end is not None:
                baseline_rel_end=results.baseline_rel_end/1000.0
            baseline_rate = get_woi_firing_rate(unit_recording, trial_start_time, trial_events, results.baseline_rel_evt,
                baseline_rel_start, baseline_rel_end, results.baseline_rel_end_evt)

            reach_woi_rel_start=0
            if results.reach_woi_rel_start is not None:
                reach_woi_rel_start=results.reach_woi_rel_start/1000.0
            reach_woi_rel_end=0
            if results.reach_woi_rel_end is not None:
                reach_woi_rel_end=results.reach_woi_rel_end/1000.0
            reach_woi_rate = get_woi_firing_rate(unit_recording, trial_start_time, trial_events, results.reach_woi_rel_evt,
                reach_woi_rel_start, reach_woi_rel_end, results.reach_woi_rel_end_evt)

            hold_woi_rel_start=0
            if results.hold_woi_rel_start is not None:
                hold_woi_rel_start=results.hold_woi_rel_start/1000.0
            hold_woi_rel_end=0
            if results.hold_woi_rel_end is not None:
                hold_woi_rel_end=results.hold_woi_rel_end/1000.0
            hold_woi_rate = get_woi_firing_rate(unit_recording, trial_start_time, trial_events, results.hold_woi_rel_evt,
                hold_woi_rel_start, hold_woi_rel_end, results.hold_woi_rel_end_evt)

            if baseline_rate is not None and reach_woi_rate is not None and hold_woi_rate is not None:

                trial_ids.append(trial_idx+1)
                rates.append(baseline_rate)
                wois.append('baseline')

                trial_ids.append(trial_idx+1)
                rates.append(reach_woi_rate)
                wois.append('reach')

                trial_ids.append(trial_idx+1)
                rates.append(hold_woi_rate)
                wois.append('hold')

                all_rates['baseline'].append(baseline_rate)
                all_rates['reach'].append(reach_woi_rate)
                all_rates['hold'].append(hold_woi_rate)

        df= pd.DataFrame({
            'trial': pd.Series(trial_ids),
            'rates': pd.Series(rates),
            'woi': pd.Series(wois),
        })
        #df.to_csv(path_or_buf='/home/jbonaiuto/%s.csv' % trial_type)

        (anova_results,pairwise)=r_one_way_anova(df,"trial","rates","woi")

        print(anova_results)
        #anova_results=pandas2ri.ri2py_dataframe(anova_results)
        #print(anova_results)
        #pairwise=pandas2ri.ri2py_dataframe(pairwise)
        return anova_results,pairwise,all_rates

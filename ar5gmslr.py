# GMSLR projection program used for IPCC WG1 AR5
# Distributed under GNU General Public License v3.0
# Originally written in IDL by Jonathan Gregory 2013
# 3.10.19 Translated from IDL to Python 2.7
# Included alternative Antarctic dynamics from the formula of Palmer et al.
# (2020, 10.1029/2019EF001413) based on the results of Levermann et al. (2014,
# 10.5194/esd-5-271-2014), used by Hermans et al. (2021, 10.1029/2020GL092064)
# Included optional alternative glaciers from the AR5 formula recalibrated
# according to results of GlacierMIP (Hock et al. 2019, 10.1017/jog.2019.22)
# 24.6.20 Upgraded to Python 3
# 18.12.20 GlacierMIP2 included, with the AR5 formula recalibrated according
# to the results of Marzeion et al. (2020, 10.1029/2019EF001470)

import cf # available from https://ncas-cms.github.io/cf-python/
import os,os.path,fnmatch
import numpy
from collections.abc import Sequence
from scipy.stats import norm

class ProjectionError(Exception):
  pass

def mSLEoGt():
# Conversion factor for Gt to m SLE
  return 1e12/3.61e14*1e-3
  
def endofhistory():
  return 2006

def vlikely_range(data):
# Compute median and 5-95% range for the first (or only) axis of data.
# Return array (stat[,dom1,...]), where stat=0,1,2 for 50-,5-,95-percentile,
# and dom1,... are any remaining axes of data.
# NB model 5-95% range is judged to be "likely" for the AR5 projections
# data -- array-like
  return numpy.percentile(data,[50,5,95],0)

def actual_range(data):
# Compute mean and actual range for the first (or only) axis of data
# Return array (stat[,dom1,...]), where stat=0,1,2 for mean,minimum,maximum
# of data, and dom1,... are any remaining axes of data.
# data -- array-like
  return numpy.array([numpy.mean(data,0),numpy.amin(data,0),\
    numpy.amax(data,0)])

def dant():
# m SLE from Antarctica during 1996 to 2005 according to AR5 chapter 4
  return (2.37+0.13)*1e-3

def dgreen():
# m SLE from Greenland during 1996 to 2005 according to AR5 chapter 4
  return (3.21-0.30)*1e-3

def fgreendyn():
# Fraction of SLE from Greenland during 1996 to 2005 assumed to result from
# rapid dynamical change, with the remainder assumed to result from SMB change
  return 0.5

def report(quantity,field=None,output=None,prefix=None,realise=False,
  uniform=False,nr=None):
# Report the likely range of a projected quantity in the last timestep and
# optionally save the timeseries of likely range and median, and the
# individual realisations of the ensemble, as CF-netCDF files.
# quantity -- str, printed name of quantity, used also to name output files
# field -- cf.Field, optional, containing the data of the quantity, assumed to
#   have time as its last dimension; if it is omitted, the quantity is
#   printed and written to the list file as given and no other action taken.
# output -- str, optional, beginning of filename for netCDF output, in whose
#   directory the list file is written, or directory for list file if field
#   is not supplied; if output is not specified, no files are written
# prefix -- str, optional, a string which is written at the start of every
#   line in the list file which is calculated from a field
# realise -- bool, optional, write output files of the ensemble as well as
#   the statistics
# uniform -- bool, optional, indicates that the quantity has a uniform
#   distribution, for which the likely range is given by the extrema; by
#   default False, in which case the likely range is 5-95% (following the
#   AR5 interpretation whereby the 5-95% range of *model* projections is taken
#   as the assessed *likely* range for the true answer)
# nr -- int, optional, indicates that each realisation on input should be
#   replicated nr times on output to file

#  if field.axis(-1,key=True)!='axistime':
#    raise ProjectionError('time should be the last dimension')

  if not field:
    print(quantity)
    if output:
      listfile=open(output+'/list','a')
      listfile.write(quantity+'\n')
      listfile.close()
    return

# Reshape as two-dimensional with time as the second dimension
  nyr=field.axis('T').size
  timeaxis=field.axis('T',key=True)
  axes=list(field.constructs.filter_by_type('domain_axis',todict='True'))
  axes=[axis for axis in axes if axis!=timeaxis]
  axes.append(timeaxis)
  field.transpose(axes,inplace=True)
  data=field.array.reshape(field.size//nyr,nyr)

# Print likely range
  vformat="%15s %6.3f [%6.3f to %6.3f]"
  if uniform:
    datarange=actual_range(data)
  else:
    datarange=vlikely_range(data)
  listline=vformat%tuple([quantity]+list(datarange[:,-1]))
  print(listline)

# Optionally write output files
  if output:
    listfile=os.path.dirname(output)+'/list'
    if prefix: listline=prefix+listline
    listfile=open(listfile,'a')
    listfile.write(listline+'\n')
    listfile.close()
    statfield=cf.Field()
    if quantity=="GMSLR":
      statfield.standard_name="global_average_sea_level_change"
    elif quantity=="expansion":
      statfield.standard_name="global_average_thermosteric_sea_level_change"
    elif quantity=="temperature":
      statfield.standard_name="surface_temperature"
    else:
      statfield.long_name="GMSLR contribution from "+\
        dict(glacier="decrease of glacier mass",
        greensmb="decrease of Greenland ice sheet mass due to change in SMB",
        greendyn="decrease of Greenland ice sheet mass "+\
        "due to rapid dynamical change",
        greennet="decrease of Greenland ice sheet mass",
        antsmb="decrease of Antarctic ice sheet mass due to change in SMB",
        antdyn="decrease of Antarctic ice sheet mass "+\
        "due to rapid dynamical change",
        antnet="decrease of Antarctic ice sheet mass",
        landwater="decrease of land water storage",
        sheetdyn="decrease of ice sheet mass due to rapid dynamical change")\
        [quantity]
    statfield.set_construct(field.axis('T'))
    statfield.set_construct(field.dim('T'))
    if quantity=="temperature": statfield.unit='K'
    else: statfield.unit='m'
    statfield.ncvar=quantity
    statfield.nc_set_variable(quantity)
    statfield.set_data(cf.Data(numpy.empty(nyr)))
    stats=dict(mid=0,lower=1,upper=2)
    for stat in stats:
      statfield.data[:]=datarange[stats[stat],:]
      cf.write(statfield,output+quantity+"_"+stat+".nc")

    if realise:
      nt=field.axis('climate_realization').size
      data=numpy.asfarray(field.array.reshape(-1,nyr),dtype='float32')
      if nr:
#       nt=data.shape[0]
        data=numpy.broadcast_to(data,(nr,nt,nyr)).copy()
        data.shape=(nr*nt,nyr)
      else:
        nr=data.shape[0]//nt
      ofield=cf.Field()
      ofield.set_data(cf.Data(data))
      ofield.set_construct(field.axis('T'))
      ofield.set_construct(field.dim('T'))
      ofield.set_construct(cf.DomainAxis(ofield.shape[0]))
      realdim=cf.DimensionCoordinate(data=\
        cf.Data(numpy.arange(ofield.shape[0],dtype='int32')),\
        properties=dict(standard_name='realization'))
      ofield.set_construct(realdim)
      climaux=cf.AuxiliaryCoordinate(data=\
        cf.Data(numpy.broadcast_to(numpy.arange(nt,dtype='int32'),\
        (nr,nt)).reshape(nr*nt)),\
        properties=dict(long_name='climate_realization'))
      climaux.nc_set_variable('climate')
      ofield.set_construct(climaux)
      if quantity in ["GMSLR","expansion","temperature"]:
        ofield.standard_name=statfield.standard_name
      else:
        ofield.long_name=statfield.long_name
      ofield.unit=statfield.unit
      ofield.ncvar=quantity
      ofield.nc_set_variable(quantity)
      cf.write(ofield,output+quantity+".nc")

def project(input=None,scenarios=None,output=None,levermann=None,**kwargs):
# input -- str, path to directory containing input files. The directory should
#   contain files named SCENARIO_QUANTITY_STATISTIC.nc, where QUANTITY is
#   temperature or expansion, and STATISTIC is mean, sd or models. Each file
#   contains one field with a dimension of time. The mean and sd fields have
#   no other dimension and are used if nt>0 (default), while the models fields
#   have a model dimension and are used if nt==0.
# scenarios -- str or sequence of str, scenarios for which projections are to be
#   made, by default all those represented in the input directory
# output, str, optional -- path to directory in which output files are to be
#   written. It is created if it does not exist. No files are written if this
#   argument is omitted.
# realise -- bool, optional, write output files of the ensemble as well as
#   the statistics
# seed -- optional, for numpy.random, default zero
# nt -- int, optional, number of realisations of the input timeseries for each
#   scenario, default 450, to be generated using the mean and sd files; specify
#   0 if the ensemble of individual models is to be used instead, which is read
#   from the models files.
# nm -- int, optional, number of realisations of components and of the sum for
#   each realisation of the input timeseries, default 1000
# tcv -- float, optional, default 1.0, multiplier for the standard deviation
#   in the input fields
# glaciermip -- optional, default False => AR5 parameters, 1 => GlacierMIP
#   (Hock et al., 2019), 2 => GlacierMIP2 (Marzeion et al., 2020)
# levermann -- optional, default None, specifies that Antarctic dynamics should
#   use the fit by Palmer et al. (2020) to the results of Levermann et al.
#   (2014); if dict, must have an key for each scenario whose value names the
#   Levermann RCP fit to be used; if str, identifies the single fit to be used
#   for every scenario; otherwise it is treated as True or False; if True the
#   scenarios must all be ones that Levermann provides.

# Check input directory
  if input is None:
    raise ProjectionError('input must be specified')
  input=os.path.expandvars(os.path.expanduser(input))
  if not os.path.isdir(input):
    raise ProjectionError('input must be an existing directory')

  if scenarios is None:
# Obtain list of scenarios from the input filenames
    bname=fnmatch.filter(os.listdir(input),'*_*.nc')
    scenarios=[tname.split('_',1)[0] for tname in bname]
    scenarios=sorted(set(scenarios))
  elif isinstance(scenarios,str):
    scenarios=[scenarios]
  else:
    scenariomsg='scenarios must be a string or sequence of strings'
    if isinstance(scenarios,Sequence):
      for scenario in scenarios:
        if not isinstance(scenario,str): raise ProjectionError(scenariomsg)
    else: raise ProjectionError(scenariomsg)

  if levermann:
    if not isinstance(levermann,str) and not isinstance(levermann,dict):
      levermann=True
  else: levermann=False
  if isinstance(levermann,dict):
    for scenario in scenarios:
      if scenario not in levermann:
        raise ProjectionError('all scenarios must have elements in levermann')
  else: levermann={scenario:levermann for scenario in scenarios}

  if output:
    output=os.path.expandvars(os.path.expanduser(output))
    if not os.path.isdir(output): os.mkdir(output)
    elif not os.access(output,os.W_OK):
      raise ProjectionError('output directory not writable: '+output)
    elif os.access(output+'/list',os.F_OK): os.unlink(output+'/list')

  for scenario in scenarios:
    report(scenario,output=output)
    project_scenario(input,scenario,output,\
      levermann=levermann[scenario],**kwargs)

def project_scenario(input,scenario,output=None,\
  seed=0,nt=450,nm=1000,tcv=1.0,\
  glaciermip=False,realise=False,levermann=False):
# Make GMSLR projection for the specified single scenario
# Arguments are all the same as project() except for:
# scenario -- str, name of the scenario
# levermann -- optional, treated as True/False to specify that Levermann
#   should be used, if str it identifies the Leverman scenario fit to be used,
#   otherwise assumed to be the scenario being simulated

  if not isinstance(scenario,str):
    raise ProjectionError('scenario must be a single string')

  numpy.random.seed(seed)

  startyr=endofhistory() # year when the timeseries for integration begin
    
# Read the input fields for temperature and expansion into txin. txin has four
# elements if nt>0: temperature mean, temperature sd, expansion mean, expansion
# sd. txin has two elements if nt==0, for temperature and expansion, each
# having a model dimension. Check that each field is one-dimensional in time,
# that the mean and sd fields for each quantity have equal time axes, that
# temperature applies to calendar years (indicated by its time bounds), that
# expansion applies at the ends of the calendar years of temperature, that
# there is no missing data, and that the model axis (if present) is the same
# for the two quantities.
  quantin=['temperature','expansion'] # input quantities
  it=0; ix=1 # indices to input quantities
  nqi=len(quantin)
  if nt==0:
    statin=['models']
    ndim=2
  else:
    statin=['mean','sd'] # input statistics
    ndim=1
  txin=[]
  for quant in quantin:
    for stat in statin:
      key=quant+'_'+stat
      file=input+'/'+scenario+'_'+key+'.nc'
      file=os.path.expandvars(os.path.expanduser(file))
      if not os.path.isfile(file):
        raise ProjectionError('missing input file: '+file)
      field=cf.read(file)[0]
      if field.ndim!=ndim:
        raise ProjectionError('field is not '+str(ndim)+\
        '-dimensional in file '+file)
      if field.dim('T') is None:
        raise ProjectionError('field does not have a time axis in file '+file)
      if ndim==2 and field.axis('ncdim%model',None) is None:
        raise ProjectionError('field does not have a model axis in file '+file)
      if field.mask.any():
        raise ProjectionError('missing data is not allowed in file '+file)
      field.override_units('1',inplace=True)
      txin.append(field)
  if nt==0:
    if not txin[it].aux('ncvar%model_name',None).\
    equals(txin[ix].aux('ncvar%model_name',None)):
      raise ProjectionError('model axes do not agree for '+quantin[it]+\
        ' and '+quantin[ix]+' in scenario '+scenario)
  else:
    for ii in [it,ix]:
      if not txin[ii*2].dim('T').equals(txin[ii*2+1].dim('T')):
        raise ProjectionError('time axes of mean and sd fields disagree for '+\
          quantin[ii]+' in scenario '+scenario)
  ttime=txin[0].dim('T')
  tbounds=ttime.bounds
  tupper=ttime.upper_bounds
  if (tbounds.month!=1 or tbounds.day!=1 \
    or tbounds.hour!=0 or tbounds.minute!=0 or tbounds.second!=0 \
    or tupper.year!=(ttime.lower_bounds.year+1)).any():
    raise ProjectionError('temperature values must be for calendar years')
  if (tupper.year[0]-1)!=startyr:
    raise ProjectionError('temperature must begin at '+str(startyr))
  if tupper.year[-1]>2100:
    raise ProjectionError('temperature input must not go beyond 2100')
  time=txin[-1].dim('T') # expansion input supplies the output time coords
  nyr=time.size
  if (time!=tupper).any():
    raise ProjectionError('expansion must be for the ends of calendar years')

# Integrate temperature to obtain K yr at ends of calendar years, replacing
# the time-axis of temperature (which applies at mid-year) with the time-axis
# of expansion (which applies at year-end)
  itin=[txin[0].copy()]
  if nt>0: itin.append(txin[1].copy())
  for field in itin:
#    field.data=cf.Data(numpy.cumsum(field.data,axis=-1))
    field.cumsum('T',inplace=True)
    field.del_construct('T')
    field.set_construct(txin[-1].dim('T'))

# Transpose the input fields to produce [realisation,time] fields
  if nt==0:
    zt=txin[0].transpose()
    zx=txin[1].transpose()
    zit=itin[0].transpose()
    zitmean=itin[0].collapse('mean','ncdim%model',squeeze=True)
    climaux=zt.aux('ncvar%model_name')
    nt=zt.axis('ncdim%model').size
    climdim=cf.DimensionCoordinate(data=cf.Data(numpy.arange(nt)),\
      properties=dict(standard_name='climate_realization'))
    zt.set_construct(climdim)
    zx.set_construct(climdim)
    zit.set_construct(climdim)

# Generate a sample of perfectly correlated timeseries fields of temperature,
# time-integral temperature and expansion, each of them [realisation,time]
  else:
    z=cf.Field()
    z.set_construct(cf.DomainAxis(nt))
    climdim=cf.DimensionCoordinate(data=cf.Data(numpy.arange(nt)),\
      properties=dict(standard_name='climate_realization'))
    z.set_construct(climdim)
    z.set_data(cf.Data(numpy.random.standard_normal(nt)*tcv))
# For each quantity, mean + standard deviation * normal random number
    zt=z*txin[1]+txin[0]
    zx=z*txin[3]+txin[2]
    zit=z*itin[1]+itin[0]
    zitmean=itin[0]

# Create a cf.Field with the shape of the quantities to be calculated
# [component_realization,climate_realization,time]
  template=cf.Field()
  template.set_construct(cf.DomainAxis(nm),'axiscomp')
  template.set_construct(cf.DomainAxis(nt),'axisclim')
  template.set_construct(cf.DomainAxis(nyr),'axistime')
  template.set_data(cf.Data(numpy.full([nm,nt,nyr],numpy.nan)),
    axes=['axiscomp','axisclim','axistime'])
  template.units='1'
  template.set_construct(txin[-1].dim('T'))
  template.set_construct(climdim,'dimclim')
  compdim=cf.DimensionCoordinate(data=cf.Data(numpy.arange(nm)),\
    properties=dict(standard_name='component_realization'))
  template.set_construct(compdim,'dimcomp')

# Obtain ensembles of projected components as cf.Field objects and add them up
  temperature=zt
  expansion=zx
  glacier=project_glacier(zitmean,zit,template,glaciermip)
  greensmb=project_greensmb(zt,template)
  greendyn=project_greendyn(scenario,template)
  greennet=greensmb+greendyn
  fraction=numpy.random.rand(nm*nt) # correlation between antsmb and antdyn
  antsmb=project_antsmb(zit,template,fraction)
  if levermann and not isinstance(levermann,str): levermann=scenario
  antdyn=project_antdyn(template,fraction,levermann,output)
  antnet=antdyn+antsmb
  sheetdyn=greendyn+antdyn
  landwater=project_landwater(template)
# put expansion last because it has a lower dimensionality and we want it to
# be broadcast to the same shape as the others rather than messing up gmslr
  gmslr=glacier+greensmb+greendyn+antnet+landwater+expansion

# Report the range of the final year and write output files if requested
  if output:
    output=output+"/"+scenario+"_"
    prefix="%-10s "%scenario
  else: prefix=''
  report("temperature",temperature,output,prefix,realise,nr=nm)
  report("expansion",expansion,output,prefix,realise,nr=nm)
  report("glacier",glacier,output,prefix,realise)
  report("greensmb",greensmb,output,prefix,realise)
  report("antsmb",antsmb,output,prefix,realise)
  report("greendyn",greendyn,output,prefix,realise,uniform=True)
  report("antdyn",antdyn,output,prefix,realise,uniform=not levermann)
  report("landwater",landwater,output,prefix,realise,uniform=True)
  report("GMSLR",gmslr,output,prefix,realise)
  report("greennet",greennet,output,prefix,realise)
  report("antnet",antnet,output,prefix,realise)
  report("sheetdyn",sheetdyn,output,prefix,realise)

  return

def project_glacier(it,zit,template,glaciermip):
# Return projection of glacier contribution as a cf.Field
# it -- cf.Field, time-integral of median temperature anomaly timeseries
# zit -- cf.Field, ensemble of time-integral temperature anomaly timeseries
# template -- cf.Field with the required shape of the output
# glaciermip -- False => AR5 parameters, 1 => fit to Hock et al. (2019),
#   2 => fit to Marzeion et al. (2020)

  startyr=int(template.dim('T').year.data[0])-1

  dmzdtref=0.95 # mm yr-1 in Marzeion's CMIP5 ensemble mean for AR5 ref period
  dmz=dmzdtref*(startyr-1996)*1e-3 # m from glacier at start wrt AR5 ref period
  glmass=412.0-96.3 # initial glacier mass, used to set a limit, from Tab 4.2
  glmass=1e-3*glmass # m SLE

  nr=template.axis('axiscomp').size
  if glaciermip:
    if glaciermip==1:
      glparm=[dict(name='SLA2012',factor=3.39,exponent=0.722,cvgl=0.15),\
        dict(name='MAR2012',factor=4.35,exponent=0.658,cvgl=0.13),\
        dict(name='GIE2013',factor=3.57,exponent=0.665,cvgl=0.13),\
        dict(name='RAD2014',factor=6.21,exponent=0.648,cvgl=0.17),\
        dict(name='GloGEM',factor=2.88,exponent=0.753,cvgl=0.13)]
      cvgl=0.15 # unnecessary default
    elif glaciermip==2:
      glparm=[dict(name='GLIMB',factor=3.70,exponent=0.662,cvgl=0.206),\
        dict(name='GloGEM',factor=4.08,exponent=0.716,cvgl=0.161),\
        dict(name='JULES',factor=5.50,exponent=0.564,cvgl=0.188),\
        dict(name='Mar-12',factor=4.89,exponent=0.651,cvgl=0.141),\
        dict(name='OGGM',factor=4.26,exponent=0.715,cvgl=0.164),\
        dict(name='RAD2014',factor=5.18,exponent=0.709,cvgl=0.135),\
        dict(name='WAL2001',factor=2.66,exponent=0.730,cvgl=0.206)]
      cvgl=0.20 # unnecessary default
    else: raise ProjectionError('unknown GlacierMIP version: '+str(glaciermip))
  else:
    glparm=[dict(name='Marzeion',factor=4.96,exponent=0.685),\
      dict(name='Radic',factor=5.45,exponent=0.676),\
      dict(name='Slangen',factor=3.44,exponent=0.742),\
      dict(name='Giesen',factor=3.02,exponent=0.733)]
    cvgl=0.20 # random methodological error
  ngl=len(glparm) # number of glacier methods
  if nr%ngl:
    raise ProjectionError('number of realisations '+\
      'must be a multiple of number of glacier methods')
  nrpergl=int(nr/ngl) # number of realisations per glacier method
  r=cf.Field()
  r.set_construct(template.axis('axiscomp'))
  r.set_construct(template.dim('dimcomp'))
  r.set_data(cf.Data(numpy.random.standard_normal(nr)))
  r.set_property('units','1')

# Make an ensemble of projections for each method
  glacier=template.copy()
  for igl in range(ngl):
# glacier projection for this method using the median temperature timeseries
    mgl=project_glacier1(it,glparm[igl]['factor'],glparm[igl]['exponent'])
# glacier projections for this method with the ensemble of timeseries
    zgl=project_glacier1(zit,glparm[igl]['factor'],glparm[igl]['exponent'])
    ifirst=igl*nrpergl
    ilast=ifirst+nrpergl
    if glaciermip: cvgl=glparm[igl]['cvgl']
    glacier[ifirst:ilast,...]=zgl+mgl*r[ifirst:ilast]*cvgl

  glacier+=dmz
  glacier.where(glacier>glmass,glmass,inplace=True)

  return glacier

def project_glacier1(it,factor,exponent):
# Return projection of glacier contribution by one glacier method
  scale=1e-3 # mm to m
  return scale*factor*(it.where(it<0,0)**exponent)

def project_greensmb(zt,template):
# Return projection of Greenland SMB contribution as a cf.Field
# zt -- cf.Field, ensemble of temperature anomaly timeseries
# template -- cf.Field with the required shape of the output

  dtgreen=-0.146 # Delta_T of Greenland ref period wrt AR5 ref period  
  fnlogsd=0.4 # random methodological error of the log factor
  febound=[1,1.15] # bounds of uniform pdf of SMB elevation feedback factor

  nr=template.axis('axiscomp').size
# random log-normal factor
  fn=numpy.exp(numpy.random.standard_normal(nr)*fnlogsd)
# elevation feedback factor
  fe=numpy.random.sample(nr)*(febound[1]-febound[0])+febound[0]
  ff=cf.Field()
  ff.set_construct(template.axis('axiscomp'))
  ff.set_construct(template.dim('dimcomp'))
  ff.set_data(cf.Data(fn*fe))
  
  ztgreen=zt-dtgreen
  greensmbrate=ff*fettweis(ztgreen)

  greensmb=greensmbrate.cumsum('T',coordinate='maximum')
  greensmb.del_construct('T')
  greensmb.set_construct(template.dim('T'))
  greensmb+=(1-fgreendyn())*dgreen()

  return greensmb

def fettweis(ztgreen):
# Greenland SMB in m yr-1 SLE from global mean temperature anomaly
# using Eq 2 of Fettweis et al. (2013)
  return (71.5*ztgreen+20.4*(ztgreen**2)+2.8*(ztgreen**3))*mSLEoGt()

def project_antsmb(zit,template,fraction=None):
# Return projection of Antarctic SMB contribution as a cf.Field
# zit -- cf.Field, ensemble of time-integral temperature anomaly timeseries
# template -- cf.Field with the required shape of the output
# fraction -- array-like, random numbers for the SMB-dynamic feedback

  nr=template.axis('axiscomp').size
  nt=template.axis('axisclim').size
# antsmb=template.copy()
# nr,nt,nyr=antsmb.shape

# The following are [mean,SD]
  pcoK=[5.1,1.5] # % change in Ant SMB per K of warming from G&H06
  KoKg=[1.1,0.2] # ratio of Antarctic warming to global warming from G&H06

# Generate a distribution of products of the above two factors
  pcoKg=(pcoK[0]+numpy.random.standard_normal([nr,nt])*pcoK[1])*\
    (KoKg[0]+numpy.random.standard_normal([nr,nt])*KoKg[1])
  meansmb=1923 # model-mean time-mean 1979-2010 Gt yr-1 from 13.3.3.2
  moaoKg=-pcoKg*1e-2*meansmb*mSLEoGt() # m yr-1 of SLE per K of global warming

  if fraction is None:
    fraction=numpy.random.rand(nr,nt)
  elif fraction.size!=nr*nt:
    raise ProjectionError('fraction is the wrong size')
  else:
    fraction.shape=(nr,nt)
#   fraction.shape=(nr,nt,1)

  smax=0.35 # max value of S in 13.SM.1.5
  ainterfactor=1-fraction*smax
  
# antsmb.data[:]=moaoKg*ainterfactor*zit.array.reshape(1,nt,-1)[:]

  z=cf.Field()
  z.set_construct(template.axis('axiscomp'),'axiscomp')
  z.set_construct(template.dim('dimcomp'))
  z.set_construct(template.axis('axisclim'),'axisclim')
  z.set_construct(template.dim('dimclim'))
  z.set_data(cf.Data(moaoKg*ainterfactor))
  antsmb=z*zit

  return antsmb

def project_greendyn(scenario,template):
# Return projection of Greenland rapid ice-sheet dynamics contribution
# as a cf.Field
# scenario -- str, name of scenario
# template -- cf.Field with the required shape of the output

# For SMB+dyn during 2005-2010 Table 4.6 gives 0.63+-0.17 mm yr-1 (5-95% range)
# For dyn at 2100 Chapter 13 gives [20,85] mm for rcp85, [14,63] mm otherwise

  if scenario in ['rcp85','ssp585']:
    finalrange=[0.020,0.085]
  else:
    finalrange=[0.014,0.063]
  return time_projection(0.63*fgreendyn(),\
    0.17*fgreendyn(),finalrange,template)+fgreendyn()*dgreen()

def project_antdyn(template,fraction=None,levermann=None,output=None):
# Return projection of Antarctic rapid ice-sheet dynamics contribution
# as a cf.Field
# template -- cf.Field with the required shape of the output
# fraction -- array-like, random numbers for the dynamic contribution
# levermann -- optional, str, use Levermann fit for specified scenario

  if levermann:
    lcoeff=dict(rcp26=[-2.881, 0.923, 0.000],\
      rcp45=[-2.676, 0.850, 0.000],\
      rcp60=[-2.660, 0.870, 0.000],\
      rcp85=[-2.399, 0.860, 0.000])
    if levermann not in lcoeff:
      raise ProjectionError(levermann+' is not available for Levermann')
    report('using Levermann '+levermann+' for antdyn',output=output)
    lcoeff=lcoeff[levermann]

    ascale=norm.ppf(1-fraction)
    final=numpy.exp(lcoeff[2]*ascale**2+lcoeff[1]*ascale+lcoeff[0])

  else: final=[-0.020,0.185]

# For SMB+dyn during 2005-2010 Table 4.6 gives 0.41+-0.24 mm yr-1 (5-95% range)
# For dyn at 2100 Chapter 13 gives [-20,185] mm for all scenarios

  return time_projection(0.41,0.20,final,template,fraction=fraction)+\
    dant()

def project_landwater(template):
# Return projection of land water storage contribution as a cf.Field

# The rate at start is the one for 1993-2010 from the budget table.
# The final amount is the mean for 2081-2100.
  nyr=2100-2081+1 # number of years of the time-mean of the final amount

  return time_projection(0.38,0.49-0.38,[-0.01,0.09],template,nyr)

def time_projection(startratemean,startratepm,final,template,\
  nfinal=1,fraction=None):
# Return projection of a quantity which is a quadratic function of time
# in a cf.Field.
# startratemean, startratepm -- rate of GMSLR at the start in mm yr-1, whose
#   likely range is startratemean +- startratepm
# final -- two-element list giving likely range in m for GMSLR at the end,
#   or array-like, giving final values, of the same shape as fraction and
#   assumed corresponding elements
# template -- cf.Field with the required shape of the output
# nfinal -- int, optional, number of years at the end over which finalrange is
#   a time-mean; by default 1 => finalrange is the value for the last year
# fraction -- array-like, optional, random numbers in the range 0 to 1,
#   by default uniformly distributed

# Create a field of elapsed time in years
  tdim=template.dim('T')
  timedata=tdim.year.data
  timedata=timedata-timedata[0]+1 # years since start
  time=cf.Field()
  time.set_construct(template.axis('T'))
  time.set_construct(tdim)
  time.set_data(timedata)

# more general than nr,nt,nyr=template.shape
  nr=template.axis('axiscomp').size
  nt=template.axis('axisclim').size
  nyr=template.axis('T').size
  if fraction is None:
    fraction=numpy.random.rand(nr,nt)
  elif fraction.size!=nr*nt:
    raise ProjectionError('fraction is the wrong size')
  data=cf.Data(fraction.reshape(nr,nt))

  fraction=cf.Field()
  fraction.set_construct(template.axis('axiscomp'),'axiscomp')
  fraction.set_construct(template.dim('dimcomp'))
  fraction.set_construct(template.axis('axisclim'),'axisclim')
  fraction.set_construct(template.dim('dimclim'))
  fraction.set_data(data)

# Convert inputs to startrate (m yr-1) and afinal (m), where both are 2-element
# arrays if finalisrange, otherwise both are arrays with the dimension of fraction
  momm=1e-3 # convert mm yr-1 to m yr-1
  startrate=(startratemean+\
    startratepm*numpy.array([-1,1],dtype=numpy.float))*momm
  finalisrange=isinstance(final,Sequence)
  if finalisrange:
    if len(final)!=2:
      raise ProjectionError('final range is the wrong size')
    afinal=numpy.array(final,dtype=numpy.float)
  else:
    if final.shape!=fraction.shape:
      raise ProjectionError('final array is the wrong shape')
    afinal=fraction.copy()
    afinal.set_data(cf.Data(final))
    startrate=(1-fraction)*startrate[0]+fraction*startrate[1]

# For terms where the rate increases linearly in time t, we can write GMSLR as
#   S(t) = a*t**2 + b*t
# where a is 0.5*acceleration and b is start rate. Hence
#   a = S/t**2-b/t
  finalyr=numpy.arange(nfinal)-nfinal+nyr+1 # last element ==nyr
# If nfinal=1, the following is equivalent to
# final/nyr**2-startrate/nyr
  acceleration=(afinal-startrate*finalyr.mean())/(finalyr**2).mean()

  if finalisrange:
# Calculate two-element list containing fields of the minimum and maximum
# timeseries of projections, then calculate random ensemble within envelope
    range=[float(acceleration[i])*(time**2)+float(startrate[i])*time \
      for i in [0,1]]
    projection=(1-fraction)*range[0]+fraction*range[1]
  else:
    projection=acceleration*(time**2)+startrate*time

  return projection

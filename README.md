# ar5gmslr

This repository contains a program called `ar5gmslr.py`, written as a [Python
3](https://docs.python.org/3) module, to compute projections of annual-mean
global-mean sea-level rise (GMSLR) for the years 2006-2100 with respect to the
time-mean of 1996-2005, given annual-mean global-mean projections of surface
air temperature change (CMIP[56] variable `tas`) and thermosteric sea-level
rise (CMIP[56] variable `zostoga`), contained in netCDF files following the [CF
convention](http://cfconventions.org). For each quantity the program requires
input timeseries of values 2006-2100 of the best estimate and uncertainty,
which are assumed to be the mean and standard deviation of a normal
distribution. By default the program uses the methods of Fifth Assessment
Report of the Intergovernmental Panel on Climate Change (AR5) Working Group I
(detailed in the [supplementary online
material](https://www.ipcc.ch/site/assets/uploads/2018/07/WGI_AR5.Chap_.13_SM.1.16.14.pdf)
of [chapter 13, Church et al.,
2013](http://dx.doi.org/10.1017/CBO9781107415324.026)).  Given AR5 input, the
program reproduces the AR5 mean and likely ranges to within 0.01 metres in all
components and the total, which is the precision stated by the AR5 for these
statistics.

The program also contains optional alternative methods for projecting the
contribution to GMSLR arising from changes in

* Antarctic ice-sheet dynamics, according to the formula of [Palmer et al.
(2020)](http://dx.doi.org/10.1029/2019EF001413), based on the results of
[Levermann et al.  (2014)](http://dx.doi.org/10.5194/esd-5-271-2014), and also
used by [Hermans et al.  (2021)](http://dx.doi.org/10.1029/2020GL092064). This
differs from the AR5 scheme in being scenario-dependent.

* The combined mass of glaciers, ice caps and the Greenland ice-sheet,
according to the AR5 formula, recalibrated either according to results of
GlacierMIP [(Hock et al., 2019)](http://dx.doi.org/10.1017/jog.2019.22) or
GlacierMIP2 [(Marzeion et al.,
2020)](http://dx.doi.org/10.1029/2019EF001470). The GlacierMIP results are based on
more and later versions of global glacier models than were available at
the time of the AR5.

By default the program tabulates the results for 2100 on `stdout`. Optionally
it can generate CF-netCDF output files containing

* annual timeseries of the median, 5- and 95-percentiles of the distributions
of each contribution and the total. (The AR5 interprets the 5-95% range of
GMSLR model projections as the assessed "likely range".)

* annual timeseries of the Monte Carlo ensemble members (by default 450,000)
of each contribution and the total.

This repository also contains directories containing input timeseries in the
form expected by the program.

* `ar5_input` for projections based on CMIP5 AOGCMs, as used in the AR5.

* `cmip6_input` for projections based on CMIP6 AOGCMs, as used by
[Hermans et al.  (2021)](10.1029/2020GL092064).

The program uses the freely available [`cf-python`
package](https://ncas-cms.github.io/cf-python) for input and output of netCDF
files and for convenience in manipulating the data in memory. To run the
program for AR5 input using all defaults:

```
import ar5gmslr # includes 'import cf' for the cf-python package
ar5gmslr.project('ar5_input') # directory in this repository
```

See the definition of the `project` function for the optional behaviours.

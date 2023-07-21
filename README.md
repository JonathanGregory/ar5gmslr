# ar5gmslr

This repository provides a [Python
3](https://docs.python.org/3) module called [`ar5gmslr.py`](./ar5gmslr.py.txt), 
containing a program to compute projections of annual-mean
global-mean sea-level rise (GMSLR) for the ends of the calendar years 2006&ndash;2009 
(or equivalently at the start of the years 2007&ndash;2100)
with respect to the
time-mean of 1996&ndash;2005, given annual global-mean projections of surface
air temperature change (CMIP[56] variable `tas`) and thermosteric sea-level
rise (CMIP[56] variable `zostoga`).

By default the program uses the methods of Fifth Assessment
Report of the Intergovernmental Panel on Climate Change (AR5) Working Group I
(detailed in the [supplementary online
material](https://www.ipcc.ch/site/assets/uploads/2018/07/WGI_AR5.Chap_.13_SM.1.16.14.pdf)
of [chapter 13, Church et al.,
2013](http://dx.doi.org/10.1017/CBO9781107415324.026)).  Given AR5 input, the
program reproduces the AR5 mean and likely ranges to within 0.01 metres in all
components and the total, which is the precision stated by the AR5 for these
statistics.

The input should be supplied in netCDF files following the [CF
convention](http://cfconventions.org)
with file names and contents
as specified in the inline documentation of the `project` function.
The `tas` values should be time-means of calendar
years 2006&ndash;2099, and `zostoga` should be values that apply at the year-ends.
The program checks that the time-coordinates and time-bounds are as expected,
and aborts if they do not conform.
For each quantity the program requires
input timeseries of either

* the best estimate and uncertainty,
which are assumed to be the mean and standard deviation of a normal
distribution, as in AR5, or

* each member of an ensemble. In this case, the sources of the ensemble members
are assumed to correspond for the two quantities, and the members are sampled
randomly with equal probability.

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
2020)](http://dx.doi.org/10.1029/2019EF001470). The GlacierMIP* results are based on
more and later versions of global glacier models than were available at
the time of the AR5.

The program tabulates the results for the final year (2100 in this case) on `stdout`, in lines of the form
"_quantity_ _mid_ `[` _lower_ `to` _upper_ `]`",
where _mid_ is the median value, and _lower_ and _upper_ the 5- and 95-percentiles of the distributions
of each contribution to GMSLR, identified by _quantity_, and the total. (The AR5 interprets the 5-95% range of
GMSLR model projections as the assessed "likely range".)
The contributions are the same as in AR5 chapter 13, thus:

| _quantity_ | description |
| --- | --- |
| temperature | Surface temperature change `tas` from input |
| expansion | Thermosteric SLR (thermal expansion) `zostoga` from input |
| glacier | Glaciers, including those peripheral to the Greenland ice-sheet |
| greensmb | Greenland ice-sheet surface mass balance, including the height-SMB feedback |
| antsmb | Antarctic ice-sheet surface masss balance, including peripheral glaciers and the interaction between SMB change and outflow |
| greendyn | Greenland ice-sheet rapid dynamics |
| antdyn | Antarctic ice-sheet rapid dynamics |
| landwater | Land water storage |
| GMSLR | Global mean sea level rise |
| greennet | Greenland ice sheet |
| antnet | Antarctic ice sheet |
| sheetdyn | Ice-sheet rapid dynamics |

The contributions listed after GMSLR are sums of other contributions, and not separately included in the total
(that would be double-counting) viz. `greennet` = `greensmb + greendyn`, `antnet` = `antsmb` + `antdyn`,
and `sheetdyn` = `greendyn` + `antdyn`.

The program optionally generates CF-netCDF output files containing

* annual timeseries of the median, 5- and 95-percentiles of each contribution and the total GMSLR.

* annual timeseries of the Monte Carlo ensemble members (by default 450,000)
of each contribution and the total, arranged in the same order for each.

See the definition of the `project` function for optional behaviours.

This repository also provides directories containing input timeseries in the
form expected by the program:

* [`ar5_input`](https://github.com/JonathanGregory/ar5gmslr/tree/main/ar5_input) for projections based the CMIP5 AOGCM ensemble, as used in the AR5.

* [`palmer20TLM_input`](https://github.com/JonathanGregory/ar5gmslr/tree/main/palmer20TLM_input) for extended CMIP5-based projections to 2300, as used by [Palmer et al. (2020)](http://dx.doi.org/10.1029/2019EF001413).

* [`cmip6_input`](https://github.com/JonathanGregory/ar5gmslr/tree/main/cmip6_input) for projections based on the CMIP6 AOGCM ensemble, as used by [Hermans et al. (2021)](10.1029/2020GL092064).

The program uses the freely available [`cf-python`
package](https://ncas-cms.github.io/cf-python) for input and output of netCDF
files and for convenience in manipulating the data in memory.
It requires cf-python version 3.14.0 (2023-01-31) or later, which uses `dask`.

To run the program for AR5 input using all defaults:

```
import ar5gmslr # includes 'import cf' for the cf-python package
ar5gmslr.project('ar5_input',output='ar5gmslr_ar5') # output is optional
```

This process takes about 2.5 minutes on a 3.4 GHz processor with 8 Gbyte RAM.
The [`stdout`](https://github.com/JonathanGregory/ar5gmslr/blob/main/ar5gmslr_ar5.stdout.txt) is consistent (within 0.01 m)
with Table 13.SM.1 of [AR5 chapter 13](https://www.ipcc.ch/site/assets/uploads/2018/07/WGI_AR5.Chap_.13_SM.1.16.14.pdf).
The [`output` directory](https://github.com/JonathanGregory/ar5gmslr/tree/main/ar5gmslr_ar5) contains a [`list` file](https://github.com/JonathanGregory/ar5gmslr/blob/main/ar5gmslr_ar5/list) with the same summary as `stdout`.
If `ensemble=True` is specified, to produce CF-netCDF files of Monte Carlo ensemble members, the output directory requires 9.7 Gbyte.
These files have not been included in this repository.

Hermans et al. (2021) produced two sets of projections from CMIP6 ensemble
input, thus:

```
import ar5gmslr # includes 'import cf' for the cf-python package
# AR5 methods
ar5gmslr.project('cmip6_input',output='ar5gmslr_cmip6')
# AR5 methods except with Antarctic dynamical ice discharge based on Levermann et al. (2014)
ar5gmslr.project('cmip6_input',levermann=dict(ssp126='rcp26',ssp245='rcp45',ssp585='rcp85'),output='ar5gmslr_cmip6_levermann')
```

This repository contains the results for both cases ([`stdout`](https://github.com/JonathanGregory/ar5gmslr/blob/main/ar5gmslr_cmip6.stdout.txt) and [`output` directory](https://github.com/JonathanGregory/ar5gmslr/tree/main/ar5gmslr_cmip6) for the AR5 methods, [`stdout`](https://github.com/JonathanGregory/ar5gmslr/blob/main/ar5gmslr_cmip6_levermann.stdout.txt) and [`output` directory](https://github.com/JonathanGregory/ar5gmslr/tree/main/ar5gmslr_cmip6_levermann) for AR5 with Levermann).
For the first case, the components and totals of GMSLR are are consistent with Table S5 in the supplementary online material of Hermans et al., and the totals of GMSLR are shown also in the first row of Table S4.
The results provided in this repository for the case with Levermann are consistent with the totals shown in the second row of Table S4, but the paper does not include the results for components in that case.

Palmer et al. (2020) made projections to 2300 using `tas` and `zostoga` estimated for RCP scenarios beyond 2100 with the two-layer model by [Palmer et al. (2018)](http://dx.doi.org/10.1088/1748-9326/aad2e4) following [Geoffroy et al. (2013)](http://dx.doi.org/10.1175/JCLI-D-12-00195.1). In this application, the rates of GMSLR due to Greenland ice sheet surface mass balance `greensmb`, Greenland ice sheet dynamics `greendyn` and Antarctic ice-sheet dynamics `antdyn` are kept constant after 2100 (`palmer=True`). The projections were made thus:

```
import ar5gmslr # includes 'import cf' for the cf-python package
ar5gmslr.project('palmer20TLM_input',palmer=True,levermann=True,output='ar5gmslr_palmer20TLM')
```

This repository contains the [`stdout`](https://github.com/JonathanGregory/ar5gmslr/blob/main/ar5gmslr_palmer20TLM.stdout.txt) and [`output` directory](https://github.com/JonathanGregory/ar5gmslr/tree/main/ar5gmslr_palmer20TLM). The output directory occupies 18 Gbyte in this case if `ensemble=True` is specified. The components of GMSLR at 2300 differ by no more than 0.02 m from the results of Palmer et al. (2020) in the 5-percentile and the median and by 0.04 m in the 95-percentile, except for `sheetdyn`, which differs by up to 0.1 m in the 95-percentile.

The program was written by [Jonathan Gregory](https://www.met.rdg.ac.uk/~jonathan) for the works cited above, some parts being originally in IDL and later translated to Python.

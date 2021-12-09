""" particulate.py
Global NEWS 2 model, GNE implementation.
Particulates sub-models.

AVAILABILITY, USE RESTRICTIONS, AND CONTACT INFORMATION
-------------------------------------------------------
The Global NEWS 2 model ("NEWS 2") and the Global NEWS modeling Environment (GNE)
were developed by the Global NEWS group and are available at our web site:
http://www.marine.rutgers.edu/globalnews/
We encourage its use for research and educational (non-commercial) purposes, but 
we request that active users contact us to inform about how it is being applied. 
Such feedback and reporting will improve our continued development of the model code. 
Global NEWS is a work group of UNESCO's Intergovernmental Oceanographic Commission (IOC).

Use of NEWS 2 should be ackwnowledged by citing Mayorga et al (in review); 
Beusen et al. (2009) and Billen and Garnier (2007) should also be cited if 
the DSi model and the ICEP index, respectively, are also used.

For questions and additional information, please contact:
Emilio Mayorga, Ph.D.          mayorga@apl.washington.edu
Applied Physics Laboratory, University of Washington
Seattle, WA  USA
---------------------------------------
1/18/2010
"""


__version__ = '$Revision: 2010-01-18$'

# Importing all numpy functions without namespace is probably expensive;
# instead, import just the functions that are used.
import numpy as ny
from numpy import sqrt, exp, log, log10
from gncfg import *
from gncore import ExportVar


# Minimum acceptable runoff (meters/yr), for erosion sources from arid basins
R_MIN = 0.003  # 3 mm/yr

# Maximum acceptable Yld_TSS_pred, approx. 2x the maximum observed TSS yield
# in the basins used to develop the regression model (Table A1 in Beusen et al 2005)
Yld_TSS_pred_MAX = 5000  # ton/km2/yr


def model(run_forms):
    """ Main body of particulates sub-models.
    """
    
    # Runoff must be in meters/yr, but current input is in mm/yr
    Rnat = IN['Rnat'] / 1000.0

    # Calculate Yld_TSS_pred and Yld_TSS, set to 0 in arid basins (Rnat < R_MIN),
    # and to Yld_TSS_pred_MAX if Yld_TSS_pred > Yld_TSS_pred_MAX
    D_TSS = IN['D_TSS']
    Yld_TSS_pred = Calc_Yld_TSS_pred()
    Yld_TSS_pred[Rnat < R_MIN] = 0.0
    Yld_TSS_pred[Yld_TSS_pred > Yld_TSS_pred_MAX] = Yld_TSS_pred_MAX

    Yld_TSS = (1 - D_TSS) * Yld_TSS_pred

    # No-data flag set when Yld_TSS = 0 or Rnat < R_MIN. Because Yld_TSS = 0 when
    # either Yld_TSS_pred = 0 or D_TSS = 1, both situations are accounted for.
    NoFluxFlg = ((Yld_TSS == 0) | (Rnat < R_MIN))
    
    # Yld_TSS is already in ton/km2/yr ...
    Ld_TSS = Yld_TSS * IN['A']

    # TSSc_pred is in mg/L: yield (Mg/km2/yr) / runoff (m/yr)  (1 L = 0.001 m3)
    # Unit conversions sort out great: (Mg/km2/yr)/(m/yr) = mg/L
    # TSSc_pred blows up when Rnat = 0, logTSSc_pred when Rnat = 0 or Yld_TSS_pred = 0.
    TSSc_pred = Yld_TSS_pred / Rnat
    logTSSc_pred = log10(TSSc_pred)

    # Correct for invalid cases (NoFluxFlg), which yield TSSpc_POC_pred errors
    TSSc_pred[NoFluxFlg] = 0
    Ld_TSS[NoFluxFlg] = 0

    # SAVE VARIABLES FOR (OPTIONAL) EXPORT TO FILE
    ExportVar(Yld_TSS, 'Yld_TSS')
    ExportVar(Ld_TSS, 'Ld_TSS')
    ExportVar(TSSc_pred, 'TSSc_pred')


    # CALCULATE %POC FOR USE IN THE PN AND PP MODELS
    # At very low TSSc_pred values (~ < 0.025 mg/L), TSSpc_POC_pred goes above 50%.
    # But such low TSSc_pred never occur in global dataset.
    TSSpc_POC_pred = -0.160*logTSSc_pred**3 + 2.83*logTSSc_pred**2 - 13.6*logTSSc_pred + 20.3
    # The TSSpc_POC_pred vs logTSSc_pred relationship from Ludwig et al is a concave-up curve,
    # with a local min. at TSSc_pred = 2250 mg/L; TSSpc_POC_pred increases at higher TSSc_pred!
    # But that makes no physical sense, and Ludwig et al actually appear to have
    # drawn a horizontal line beyond that point in their Fig. 3. This bottoming
    # out of TSSpc_POC_pred at high TSS conc. is generally supported by the literature.
    # It could be implemented like this:   TSSpc_POC_pred[TSSc_pred > 2250] = 0.5
    # However, the Yld_TSS_pred_MAX implementations makes that unnecessary.
    TSSpc_POC_pred[NoFluxFlg] = 0

    # nutrient form list is limited to particulate and actual 
    # model run forms ('parameters') in RUN['F']
    for F in run_forms:

        # Calculate POC, PN, PP
        if F in ('POC', 'PN'):
            if F == 'POC':
                TSSpc_F_pred = TSSpc_POC_pred
            elif F == 'PN':
                TSSpc_F_pred  = 0.116*TSSpc_POC_pred - 0.019

            # Correct for invalid cases (NoFluxFlg), which give TSSpc_POC_pred errors.
            # Then calculate POC & PN yields (kg/km2/yr) and loads (ton/yr)
            TSSpc_F_pred[NoFluxFlg] = 0

            # PARTICULATE YIELD (kg/km2/yr) & LOAD (T/yr, or Mg/yr)
            # The Yld_F equation below is derived from these 3 equations:
            # Yld_TSS = (1 - D_TSS) * Yld_TSS_pred
            # Yld_F_pred = (TSSpc_F_pred/100)*(1000*Yld_TSS_pred)
            # Yld_F = (1 - D_TSS)*Yld_F_pred
            Yld_F = (TSSpc_F_pred/100)*(1000*Yld_TSS)
            Ld_F  = Yld_F * IN['A'] / 1000.0
        elif F == 'PP':
            # Pre-calculate POCload for use in the PP model equation (eq. 4).
            # In original PP equation (eq 4), POC and PP loads are in kg/yr,
            # not the usual ton/yr used in GNE for nutrient loads. Here,
            # a conversion factor is applied so Ld_F is in ton/yr.
            # POCload is calculated for "natural" conditions (pre-dam; no trapping).
            Ld_POC_pred_kgyr = 1000*(TSSpc_POC_pred/100)*Ld_TSS/(1 - D_TSS)  # in kg/yr
            Ld_F_pred = exp(-3.09614 + 1.001769*log(Ld_POC_pred_kgyr)) / 1000.0
            
            # PARTICULATE YIELD (kg/km2/yr) & LOAD (T/yr, or Mg/yr)
            # Now calculate Ld_F with sediment trapping
            Ld_F = (1 - D_TSS) * Ld_F_pred

            # Correct for invalid cases (NoFluxFlg), which give TSSpc_POC_pred and therefore
            # Ld_F & Yld_F errors. Then calculate PP yield (kg/km2/yr) & percent (%)
            Ld_F[NoFluxFlg] = 0

            Yld_F = 1000.0 * Ld_F / IN['A']
            TSSpc_F_pred = 100 * Yld_F / (1000*Yld_TSS)
            TSSpc_F_pred[NoFluxFlg] = 0


        # CN = (TSSpc_POC_pred/12)/(PNpct/14) # Molar C:N ratio; calculate C:P and N:P ratios?

        # SAVE VARIABLES FOR (OPTIONAL) EXPORT TO FILE
        ExportVar(TSSpc_F_pred, 'TSSpc_pred', F)
        ExportVar(Yld_F, 'Yld', F)
        ExportVar(Ld_F, 'Ld', F)


def Calc_Yld_TSS_pred():
    """ Calculate pre-dam TSS yield, Yld_TSS_pred.
    """

    # Truncate (clip) input (independent) variables to the acceptable range 
    # before using in Yld_TSS_pred equation
    IndepVarsTruncate = lambda var,minval,maxval: IN[var].clip(min=minval,max=maxval)
    MargGrassPrc = IndepVarsTruncate('marggrass',0,84.6865)
    WetlnRicePrc = IndepVarsTruncate('wetlndrice',0,24.7206)
    FrnrPrecp    = IndepVarsTruncate('frnrprecp',0.854985,11.1682)
    FrnrSlope    = IndepVarsTruncate('frnrslope',1.1301,38.4531)

    # The input lithology variable corresponds to the class number of the
    # *dominant* lithology class in the basin (from Amiotte-Suchet et al, 2003)
    # 2=carbonate rocks, 3=shales, 4=plutonic/metamorphic (shield), 
    # 6=acid volcanic rock, 7=basalt
    # not used (?): 1=sand/sanstone, 5=gabbros, 8=ice
    # If the basin did not overlay on the lithology map, a "dummy" lithology
    # class number 8 (ice) was assigned. See LithologySlope.xls.
    LithoChemCoef = {1:0.0, 2:1.0379,  3:0.9037, 4:0.3125, \
                     5:0.0, 6:-2.0678, 7:0.6694, 8:0.0}
    # Map dominant lithology class number to corresponding coefficient
    LiClass = IN['LiClass']
    LithoChem = [LithoChemCoef[i] for i in LiClass]


    # YIELD (ton/km2/yr) & LOAD (ton/yr), where 1 ton = 1 Mg
    Yld_TSS_pred = exp(0.0301*MargGrassPrc + 0.1234*WetlnRicePrc + \
                   0.2933*FrnrPrecp + 0.1027*FrnrSlope + LithoChem + 0.5522)
    # Set yield to 0 if lithology class is 8 (see comments above)
    Yld_TSS_pred[LiClass == 8] = 0.0
    
    return Yld_TSS_pred


if __name__ == '__main__':
    # main() or this script file can't be called directly
    print "Error: particulate.py can't be run directly. Use globalnews.py instead"
    sys.exit()

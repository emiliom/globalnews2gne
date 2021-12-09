""" dissolved.py
Global NEWS 2 model, GNE implementation.
Dissolved sub-models.

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
from numpy import sqrt, exp, log
from gncfg import *
from gncore import ExportVar

# minimum acceptable runoff (meters/yr), for diffuse sources from arid basins
R_MIN = 0.003  # 3 mm/yr


def model(run_forms):
    """ Dissolved nutrient form sub-models.
    """
    
    # nutrient form list is limited to dissolved and actual 
    # model run forms ('parameters') in RUN['F']
    for F in run_forms:
        # DSi is implemented as a separate, isolated function.
        if F == 'DIC':
            Yld_F = DICModel()   # Currently an empty function.
        elif F == 'DSi':
            Yld_F = DSiModel()
        else:
            # POINT (SEWAGE) SOURCES
            RSpnt_E, FEpnt_F = Calc_PointSources(F)
            RSpnt_F = FEpnt_F * RSpnt_E

            # DIFFUSE (NON-POINT) SOURCES
            # Calculate FEws_F, FEws_nat,F, f_F(Rnat)
            FEws_F, FEws_nat_F, f_F = Calc_WSExportFunc(F)
            
            # Diffuse River Sources: explicit
            WSdif_ant_E, WSdif_nat_E = Calc_WSdifExplicit(F)
            RSdif_expl_ant_F =     FEws_F * WSdif_ant_E
            RSdif_expl_nat_F = FEws_nat_F * WSdif_nat_E
            
            # Diffuse River Sources: export coefficient
            RSdif_ec_F = Calc_RSdifExportCoeff(f_F, F)
            if F == 'DOC':
                RSdif_ec_ant_F = 0.0
                RSdif_ec_nat_F = RSdif_ec_F
            else:
                Agfr = IN['agric'] / 100.0
                RSdif_ec_ant_F =      Agfr  * RSdif_ec_F
                RSdif_ec_nat_F = (1 - Agfr) * RSdif_ec_F
            
            # Total diffuse River Sources: anthropogenic vs. natural
            RSdif_ant_F = RSdif_expl_ant_F + RSdif_ec_ant_F
            RSdif_nat_F = RSdif_expl_nat_F + RSdif_ec_nat_F

            # DISSOLVED YIELD (kg/km2/yr)
            FEriv_F = Calc_FEriv(F)

            #RS_ant_F = RSpnt_F + RSdif_ant_F
            #RSdif_F  = RSdif_ant_F + RSdif_nat_F
            Yld_F = FEriv_F * (RSpnt_F + (RSdif_ant_F + RSdif_nat_F))


            # SAVE VARIABLES FOR (OPTIONAL) EXPORT TO FILE
            # Some are saved into global OUT dictionary mainly for reuse in SourceContrib()
            ExportVar(RSdif_ec_ant_F, 'RSdif_ec_ant', F)
            ExportVar(RSdif_ec_nat_F, 'RSdif_ec_nat', F)
            ExportVar(RSdif_ant_F, 'RSdif_ant', F)
            ExportVar(RSdif_nat_F, 'RSdif_nat', F)
            ExportVar(RSpnt_F, 'RSpnt', F)


            # CALCULATE SOURCE CONTRIBUTIONS
            SourceContrib(F)

        # DISSOLVED LOAD (ton/yr, or Mg/yr)
        Ld_F = Yld_F * IN['A'] / 1000.0
        
        # SAVE VARIABLES FOR (OPTIONAL) EXPORT TO FILE
        ExportVar(Yld_F, 'Yld', F)
        ExportVar(Ld_F, 'Ld', F)


def DSiModel():
    """ DSi model. A multiple linear regression model, from Beusen et al. (2009)
    """

    # Runoff must be in meters/yr, but current input is in mm/yr
    Rnat = IN['Rnat'] / 1000.0

    # Truncate (clip) input (independent) variables to the acceptable range 
    # before using in T_DSiyldNAT equation
    IndepVarsTruncate = lambda var,minval,maxval: IN[var].clip(min=minval,max=maxval)
    Precip     = IndepVarsTruncate('precip',0.519952,10.9972)
    GaezSlope  = IndepVarsTruncate('gslope',1.95543000000000,41.9841000000000)
    BulkDens   = IndepVarsTruncate('bulkdens',0.93677500000000,1.6459700000000)
    VolcLithFr = IndepVarsTruncate('frvolclith',0.00000000000000,0.7621180000000)

    # CALCULATE BOX-COX TRANSFORMED ("T_") YIELD (ton SiO2/km2/yr), pre-dam
    T_Yld_DSi_pred = 1.60765821573*log(Precip) + 0.03099949128*GaezSlope + \
                     -2.59587868714*BulkDens + 1.69157777610*VolcLithFr + 2.56118766111
    
    # CALCULATE UN-TRANSFORMED YIELD (ton SiO2/km2/yr)
    boxcox_lambda = 0.068623051867468
    Yld_DSi_pred = (boxcox_lambda*T_Yld_DSi_pred + 1) ** (1/boxcox_lambda)

    # Set Yld_DSi_pred to 0 in arid basins (Rnat < R_MIN)
    Yld_DSi_pred[Rnat < R_MIN] = 0.0
    
    # Set yield to 0 if bulk density is ~ 0
    Yld_DSi_pred[IN['bulkdens'] < 0.01] = 0.0

    # Unit conversion of yield, to kg Si/km2/yr
    Yld_DSi_pred *= 1000*(28.09/60.09)

    # Apply reservoir retention term (currently from TSS only)
    D_TSS = IN['D_TSS']
    Yld_DSi = (1 - D_TSS) * Yld_DSi_pred

    return Yld_DSi


def DICModel():
    """ DIC model. Function currently empty; DIC model development is being
    done elsewhere.
    """
    print "Blank DIC model function. DIC model development is being done elsewhere."
    return 0


def Calc_PointSources(F):
    """ Calculate point source/sewage variables.
    """

    ccalf = CCAL[F]
    
    # element (N, P, C)
    E = F[-1]

    # FEpnt_F
    if F == 'DIN':
        # IN['hwfrem_N_aspct'] is in %, not 0-1
        hwfrem_E = IN['hwfrem_N_aspct'] / 100.0
        hwfrem_E_max = 0.8
        FEpnt_F = 0.485 + 0.255*(hwfrem_E/hwfrem_E_max)
    else:
        FEpnt_F = ccalf['c']

    # RSpntExc_E
    if E in ('N', 'P'):
        RSpntExc_E = IN['RSpntExc_'+E]
    else:
        RSpntExc_E = 0.0

    # RSpntDet_E
    if E == 'P':
        RSpntDet_E = IN['RSpntDet_P']
    else:
        RSpntDet_E = 0.0


    # RSpnt_E (total)
    RSpnt_E = RSpntExc_E + RSpntDet_E
    
    # SAVE VARIABLES FOR (OPTIONAL) EXPORT TO FILE
    # Some are saved into global OUT dictionary mainly for reuse in SourceContrib()
    ExportVar(RSpntExc_E, 'RSpntExc_'+E, F)
    ExportVar(RSpntDet_E, 'RSpntDet_'+E, F)
    ExportVar(RSpnt_E, 'RSpnt_'+E, F)
    ExportVar(FEpnt_F, 'FEpnt', F)

    return RSpnt_E, FEpnt_F


def Calc_WSExportFunc(F):
    """ Calculate Watershed Export Fraction (land -> rivers)
    FEws_F is a function of 'natural' mean annual water runoff from land to streams (Rnat):
    FEws_F = e_F * f_F(Rnat)
    """

    ccalf = CCAL[F]
    Rnat = IN['Rnat'] / 1000.0 # Runoff must be in meters/yr, but input is in mm/yr

    # Calculate f_F runoff function
    if F in ('DIN', 'DON', 'DOP', 'DOC'):
        f_F = Rnat ** ccalf['a']
    else:  # DIP
        # Zero values will cause rattn to blow up (error) for DIP formulation,
        # where exponent is negative. More generally: f_F -> 0 as Rnat -> 0.
        # Net effect of setting near-zero Rnat values to a very low min value
        # is to set f_F ~ 0 as Rnat -> 0
        Rgt0 = Rnat
        Rgt0[Rnat < 0.00001] = 0.0000001
        f_F = 1/(1 + (Rgt0/ccalf['a']) ** -ccalf['b'])
    
    # Set f_F (and therefore FEws_F and FEws_nat_F) to 0 for arid basins, 
    # using the runoff threshold R_MIN (Rnat < R_MIN)
    # Point sources in N & P models can produce yield > 0 when Rnat = 0 (more 
    # generally, Rnat < R_MIN). But DOC model has no point sources, so yield = 0
    # when Rnat = 0 (Rnat < R_MIN). This creates an inconsistency for DOM yields.
    f_F[Rnat < R_MIN] = 0.0

    FEws_F = ccalf['e'] * f_F

    # Initialize FEws_nat_F to be identical to FEws_F.
    # Differentiation for DIN will be applied in the DIN block below.
    # copy() is needed to preserve FEws_F (numpy's default is copy-by-reference)
    FEws_nat_F = FEws_F.copy()

    # Enforcing a maximum value
    # This constraint was set for DIN only, but if this parameter is going to be
    # interpreted as a "Fraction Exported", logically it should be <= 1.
    # However, that's not how the other models where originally defined and calibrated.
    # In general, all models exhibit FEws_F < 1

    # For DIN, enforce max value for FEws_F and calculate final FEws_nat_F
    if F == 'DIN':
        FEws_F[FEws_F > 1.0] = 1.0

        # FEws_nat. Currently only applies
        # in basins predominantly in the Humid Tropics
        HumidTropicsMask = (IN['KoppenGrpAperc'] > 50)
        FEws_nat_F[HumidTropicsMask] = ccalf['enat'] * f_F[HumidTropicsMask]
        # This constraint is probably implicit, but enforcing
        # it explicitly is a good, safe practice
        FEws_nat_F[FEws_nat_F > 1.0] = 1.0
    
    # SAVE VARIABLES FOR (OPTIONAL) EXPORT TO FILE
    ExportVar(FEws_F, 'FEws', F)
    ExportVar(FEws_nat_F, 'FEws_nat', F)

    return FEws_F, FEws_nat_F, f_F


def Calc_FEriv(F):
    """ Calculate River Export fraction (loss along the river network)
    from individual retention (loss) terms
    """

    # L_F, river retention
    if F == 'DIN':
        A = IN['A']
        L_F = 0.0605 * log(A) - 0.0443
        # Enforce max value
        L_F[L_F > 0.65] = 0.65
    else:
        L_F = 0

    # D_F, reservoir retention
    # Basin D_F values are pre-processed before use in GNE.
    # Calculated from each reservoir i, then aggregated to basin as:
    # D_F = (1/Q)Sum(i=1-n)[D_i_F * Q_i]
    if F == 'DIN':
        D_F = IN['D_DIN']
        # Enforce max value
        D_F[D_F > 0.965] = 0.965
    elif F == 'DIP':
        D_F = IN['D_DIP']
        # Enforce max value
        D_F[D_F > 0.85] = 0.85
    else:  # DON, DOP, DOC
        D_F = 0

    # FQrem, consumptive water use
    FQrem = IN['FQrem']
    
    # FEriv_F
    FEriv_F = (1 - L_F)*(1 - D_F)*(1 - FQrem)

    # Enforce FEriv_F max value
    # This constraint was originally set for DIN only, but if this parameter will
    # be interpreted as a "Fraction Exported", logically it should be <= 1.
    # However, that's not how the other models where defined and calibrated.
    if F == 'DIN':
        FEriv_F[FEriv_F > 1.0] = 1.0

    # SAVE VARIABLES FOR (OPTIONAL) EXPORT TO FILE
    ExportVar(FEriv_F, 'FEriv', F)

    return FEriv_F


def Calc_RSdifExportCoeff(f_F, F):
    """ Diffuse River Sources: export coefficient
    """
    
    ccalf = CCAL[F]
    
    if F in ('DIP', 'DON', 'DOP'):
        EC_F = ccalf['EC']
        RSdif_ec_F = f_F * EC_F
    elif F == 'DIN':
        RSdif_ec_F = 0.0
    else:  # DOC
        Wfr = IN['W_pct'] / 100.0  # Wfr is expected to be a fraction (0-1)
        EC_wet_F, EC_dry_F = ccalf['EC_wet'], ccalf['EC_dry']
        RSdif_ec_wet_F = f_F * (     Wfr  * EC_wet_F)
        RSdif_ec_dry_F = f_F * ((1 - Wfr) * EC_dry_F)
        RSdif_ec_F = RSdif_ec_wet_F + RSdif_ec_dry_F

        # Save into global OUT dictionary for reuse in SourceContrib()
        ExportVar(RSdif_ec_wet_F, 'RSdif_ec_wet', F)
        ExportVar(RSdif_ec_dry_F, 'RSdif_ec_dry', F)

    return RSdif_ec_F


def Calc_WSdifExplicit(F):
    """ Diffuse River Sources: explicit
    """

    ccalf = CCAL[F]

    # element (N, P, C)
    E = F[-1]
    
    if E in ('N', 'P'): # DIN, DIP, DON, DOP
        WSdif_fe_E = IN['WSdif_fe_'+E]
        WSdif_ma_E = IN['WSdif_ma_'+E]
        WSdif_ex_E = IN['WSdif_ex_'+E]
        
        WSdif_ant_E = WSdif_fe_E + WSdif_ma_E - WSdif_ex_E
        WSdif_nat_E = 0.0
        if F == 'DIN':
            # WSdif_fix_E and WSdif_dep_E are each provided as two separate input files,
            # nat & agr (ant)
            WSdif_fix_ant_E = IN['WSdif_fix_ant_N']
            WSdif_dep_ant_E = IN['WSdif_dep_ant_N']
            WSdif_ant_E += WSdif_fix_ant_E + WSdif_dep_ant_E
            
            WSdif_fix_nat_E = IN['WSdif_fix_nat_N']
            WSdif_dep_nat_E = IN['WSdif_dep_nat_N']
            WSdif_nat_E = WSdif_fix_nat_E + WSdif_dep_nat_E

        # Enforce WSdif_ant_E min value for net inputs balance.
        # WSdif_nat_E is always >= 0
        WSdif_ant_E[WSdif_ant_E < 0.0] = 0  # 0.0
    else:  # DOC
        WSdif_ant_E = 0.0
        WSdif_nat_E = 0.0


    # SAVE VARIABLES FOR (OPTIONAL) EXPORT TO FILE
    ExportVar(WSdif_ant_E, 'WSdif_ant_'+E, F)
    ExportVar(WSdif_nat_E, 'WSdif_nat_'+E, F)

    return WSdif_ant_E, WSdif_nat_E


# =====================================================================

def SourceContrib(F):
    """ Determine Source Distribution (apportionment) and dominant (max) source.
    """
    
    ccalf = CCAL[F]

    # element (N, P, C)
    E = F[-1]

    # Differentiate between retention from agricultural vs. natural sources
    # (though currently this is relevant only for DIN, and only 
    # in basins predominantly in the Humid Tropics
    FEriv      = OUT[F + 'FEriv']
    FErivws    = FEriv * OUT[F + 'FEws']
    FErivwsnat = FEriv * OUT[F + 'FEws_nat']

    RSdif_ant_F = OUT[F + 'RSdif_ant']
    RSdif_nat_F = OUT[F + 'RSdif_nat']

    YS1dif_ant_F = FEriv * RSdif_ant_F
    YS1dif_nat_F = FEriv * RSdif_nat_F
    YS1pnt_F     = FEriv * OUT[F + 'FEpnt'] * OUT[F + 'RSpnt_'+E]
    
    # coarse-level source attribution
    YS1MaxDict_F = {0:'YS1pnt', 1:'YS1dif_ant', 2:'YS1dif_nat'}
    YS1all = ny.vstack((YS1pnt_F, YS1dif_ant_F, YS1dif_nat_F))

    if E in ('N', 'P'):  # DIN, DIP, DON, DOP
        # Load variables that are used by all/most N & P models
        WSdif_fe_E = IN['WSdif_fe_'+E]
        WSdif_ma_E = IN['WSdif_ma_'+E]
        WSdif_ex_E = IN['WSdif_ex_'+E]

        # Calculate gross diffuse anthropogenic land inputs, WSdif_gross_ant_E
        # Account for cases where WSdif_gross_ant_E (expfr denominator) is 0
        if F == 'DIN':
            WSdif_gross_ant_E = OUT[F + 'WSdif_ant_'+E] + WSdif_ex_E
        else:
            WSdif_gross_ant_E = WSdif_fe_E + WSdif_ma_E
        expfr = ny.where(WSdif_gross_ant_E > 0.0, WSdif_ex_E/WSdif_gross_ant_E, 1.0)
        G = 1. - expfr
        # Impose "mass-balance" constraint on G
        # (equivalent to WSdif_ant_E[WSdif_ant_E < 0.0] = 0.0)
        G[G < 0.0] = 0.0

        YS2difMa_ant_F = (FErivws * WSdif_ma_E) * G
        YS2difFe_ant_F = (FErivws * WSdif_fe_E) * G

        YS2pntExc_F = FEriv * OUT[F + 'FEpnt'] * OUT[F + 'RSpntExc_'+E]

        if F == 'DIN':
            WSdif_fix_ant_E = IN['WSdif_fix_ant_N']
            WSdif_dep_ant_E = IN['WSdif_dep_ant_N']
            WSdif_fix_nat_E = IN['WSdif_fix_nat_N']
            WSdif_dep_nat_E = IN['WSdif_dep_nat_N']

            YS2difFix_ant_F = (FErivws * WSdif_fix_ant_E) * G
            YS2difDep_ant_F = (FErivws * WSdif_dep_ant_E) * G
            
            # "Natural" sources (no crop export to account for)
            YS2difFix_nat_F = FErivwsnat * WSdif_fix_nat_E
            YS2difDep_nat_F = FErivwsnat * WSdif_dep_nat_E
            
            # fine-level source attribution
            YS2MaxDict_F = {0:'YS2pntExc', 1:'YS2difFe_ant', 2:'YS2difMa_ant', 
                            3:'YS2difFix_ant', 4:'YS2difDep_ant',
                            5:'YS2difFix_nat', 6:'YS2difDep_nat'}
            YS2all = ny.vstack((YS2pntExc_F, YS2difFe_ant_F, YS2difMa_ant_F, 
                                YS2difFix_ant_F, YS2difDep_ant_F, 
                                YS2difFix_nat_F, YS2difDep_nat_F))
        else:  # DIP, DON, DOP
            # Weathering/"Leaching" from agricultural areas
            # at same rate as in natural systems
            YS2dif_ec_ant_F = FEriv * OUT[F + 'RSdif_ec_ant']

            # Weathering/"Leaching" from "natural" areas (no crop export)
            # For these nutrient forms, all diffuse inputs in natural areas 
            # is from YS1dif_nat_F
            YS2dif_ec_nat_F = YS1dif_nat_F

            # fine-level source attribution
            # Use different names for weathering and leaching
            if F == 'DIP':
                LchWth = 'Wth'
            else:
                LchWth = 'Lch'
            
            if F == 'DON':
                YS2MaxDict_F = {0:'YS2pntExc', 1:'YS2difFe_ant', 2:'YS2difMa_ant', 
                                3:'YS2dif'+LchWth+'_ant', 4:'YS2dif'+LchWth+'_nat'}
                YS2all = ny.vstack((YS2pntExc_F, YS2difFe_ant_F, YS2difMa_ant_F, 
                                    YS2dif_ec_ant_F, YS2dif_ec_nat_F))
            else:
                # YS2pntDet_F is 0 for N
                YS2pntDet_F = FEriv * OUT[F + 'FEpnt'] * OUT[F + 'RSpntDet_'+E]

                YS2MaxDict_F = {0:'YS2pntExc', 1:'YS2pntDet', 
                                2:'YS2difFe_ant', 3:'YS2difMa_ant', 
                                4:'YS2dif'+LchWth+'_ant', 5:'YS2dif'+LchWth+'_nat'}
                YS2all = ny.vstack((YS2pntExc_F, YS2pntDet_F, YS2difFe_ant_F, YS2difMa_ant_F,
                                    YS2dif_ec_ant_F, YS2dif_ec_nat_F))
    else: # DOC
        # just wetlands vs. non-wetlands (dry)
        YS2difWet_F = FEriv * OUT[F + 'RSdif_ec_wet']
        YS2difDry_F = FEriv * OUT[F + 'RSdif_ec_dry']

        YS2MaxDict_F = {0:'YS2difWet', 1:'YS2difDry'}
        YS2all = ny.vstack((YS2difWet_F, YS2difDry_F))


    # SAVE VARIABLES FOR (OPTIONAL) EXPORT TO FILE

    # SELECT AND EXPORT MAX SOURCE
    # When all src* arrays are zero, srcMax is assigned the value "undef"
    YS2MaxIdx_F = YS2all.argmax(0)
    YS2Max_F = ny.array([YS2MaxDict_F[src] for src in YS2MaxIdx_F], dtype='|S15')
    YS2Max_F[YS2all.max(0) == 0] = 'undef'
    ExportVar(YS2Max_F, 'YS2Max', F)

    if E in ('N', 'P'):  # DIN, DIP, DON, DOP
        YS1MaxIdx_F = YS1all.argmax(0)
        YS1Max_F = ny.array([YS1MaxDict_F[src] for src in YS1MaxIdx_F], dtype='|S12')
        YS1Max_F[YS1all.max(0) == 0] = 'undef'
        ExportVar(YS1Max_F, 'YS1Max', F)

        ExportVar(YS1pnt_F, 'YS1pnt', F)
        ExportVar(YS1dif_ant_F, 'YS1dif_ant', F)
        ExportVar(YS1dif_nat_F, 'YS1dif_nat', F)

        ExportVar(YS2pntExc_F, 'YS2pntExc', F)
        if E == 'P':  # DIP, DOP
            ExportVar(YS2pntDet_F, 'YS2pntDet', F)

        ExportVar(YS2difMa_ant_F, 'YS2difMa_ant', F)
        ExportVar(YS2difFe_ant_F, 'YS2difFe_ant', F)
        if F == 'DIN':
            ExportVar(YS2difFix_ant_F, 'YS2difFix_ant', F)
            ExportVar(YS2difDep_ant_F, 'YS2difDep_ant', F)
            ExportVar(YS2difFix_nat_F, 'YS2difFix_nat', F)
            ExportVar(YS2difDep_nat_F, 'YS2difDep_nat', F)
        else:  # DIP, DON, DOP
            ExportVar(YS2dif_ec_ant_F, 'YS2dif'+LchWth+'_ant', F)
            ExportVar(YS2dif_ec_nat_F, 'YS2dif'+LchWth+'_nat', F)
    else: # DOC
        ExportVar(YS2difWet_F, 'YS2difWet', F)
        ExportVar(YS2difDry_F, 'YS2difDry', F)



if __name__ == '__main__':
    # main() or this script file can't be called directly
    print "Error: dissolved.py can't be run directly. Use globalnews.py instead"
    sys.exit()

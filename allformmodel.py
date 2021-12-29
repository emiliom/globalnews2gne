""" allformmodel.py
Global NEWS 2 model, GNE implementation.
Model components or calculations incorporating all nutrient forms.

Model or calculations performed after all Global NEWS
nutrient form sub-models have been executed, and the output variables
are available in memory through the OUT[] global dictionary.

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


# Importing all numpy functions without namespace is probably expensive;
# instead, import just the functions that are used.
import numpy as ny
from numpy import sqrt, exp, log
from gncfg import *
from gncore import ExportVar


def model():
    """ Calculate ICEP, Gilles Billen's and Josette Garnier's
        Index of Coastal Eutrophication Potential.
    """
    
    # modeled yields in kg km-2 yr-1,
    TNyld  = OUT['DINYld'] + OUT['DONYld'] + OUT['PNYld']
    TPyld  = OUT['DIPYld'] + OUT['DOPYld'] + OUT['PPYld']
    DSiyld = OUT['DSiYld']
    
    # Calculate ICEP in kg C km-2 day-1
    # First use yields in kg km-2 yr-1, then convert from yr-1 to day-1
    # (1.0/365.0 multiplier)
    NPratio = (TNyld/14)/(TPyld/31)
    
    ICEP = ny.where(NPratio < 16, (TNyld/(14*16) - DSiyld/(28*20)), \
                                  (TPyld/31 - DSiyld/(28*20)) )
    ICEP *= 106*12 * (1.0/365.0)
    
    # Set ICEP to -999 (no data) if DSiyld is 0
    ICEP[DSiyld < 0.0001] = -999

    # SAVE VARIABLES FOR (OPTIONAL) EXPORT TO FILE
    ExportVar(ICEP, 'ICEP')


if __name__ == '__main__':
    # main() or this script file can't be called directly
    print "Error: allformmodel.py can't be run directly. Use globalnews.py instead"
    sys.exit()

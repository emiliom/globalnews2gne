README.txt
Model code package for the Global NEWS 2 model ("NEWS 2") 
and Global NEWS modeling Environment ("GNE")
http://www.marine.rutgers.edu/globalnews/GNE/
1/18/2010

MODEL PACKAGE DESCRIPTION
-------------------------

The files distributed in GlobalNEWS2model.zip contain the model code and sample inputs and outputs for the Global NEWS 2 model, as implemented in the Global NEWS modeling Environment. NEWS 2 is described in Mayorga et al. (in review), while its DSi sub-model is described in Beusen et al (2009) and the ICEP eutrophication index is described in Billen and Garnier (2007). The code included in this package is an updated implementation of the NEWS 2 and DSi code used in the corresponding publications; results for NEWS 2 (excluding DSi) are largely identical to those discussed in Mayorga et al. (in review) and Seitzinger et al. (in press), while only minor differences are expected for DSi results as discussed in Beusen et al. (2009).

GNE is written in Python. See the user manual, NEWS2_GNEManual.pdf, for an extensive description of GNE and its component code and configuration files, file organization, installation instructions (including help with Python installation and versions), how to set up and execute a model run, etc; although the manual corresponds to a previous version of the model code, there are only small differences. The most important new feature is the integration of the DSi sub-model and the optional code file "allformmodel.py" called via the run-time argument "--afm". The all-forms feature enables calculations across nutrient forms, and currently it includes an implementation of the ICEP index.

Two additional components of GNE mentioned in the manual (GIS pre-processing and model post-processing) are not available in this package. They do not represent model components per se, but rather aids in preparing basin-aggregated inputs and in analyzing model outputs. They will be included in a future package.

To facilitate the use of NEWS 2, sample basin-aggregated input files have been included, corresponding to the year 2000 simulated hydrology version described in Mayorga et al. (in review) and the DSi model run from Beusen et al (2009). The associated NEWS 2/GNE model configuration files (*.cfg) are set up for this model run and were used to create the model output file that is included. See the user manual first. The source of each input variable is described in Mayorga et al. (in review).


AVAILABILITY, USE RESTRICTIONS, AND CONTACT INFORMATION
-------------------------------------------------------

The Global NEWS 2 model ("NEWS 2") and the Global NEWS modeling Environment (GNE) were developed by the Global NEWS group and are available at our web site:
http://www.marine.rutgers.edu/globalnews/
We encourage its use for research and educational (non-commercial) purposes, but we request that active users contact us to inform about how it is being applied. Such feedback and reporting will improve our continued development of the model code. Global NEWS is a work group of UNESCO's Intergovernmental Oceanographic Commission (IOC).

Use of NEWS 2 should be ackwnowledged by citing Mayorga et al (in review); Beusen et al. (2009) and Billen and Garnier (2007) should also be cited if the DSi model and the ICEP index, respectively, are also used.

For questions and additional information, please contact:
Emilio Mayorga, Ph.D.          mayorga@apl.washington.edu
Applied Physics Laboratory, University of Washington
Seattle, WA  USA


RELEVANT PUBLICATIONS
---------------------

The three Global NEWS publications from the list below (Beusen et al, Mayorga et al, and Seitzinger et al) will be available soon or upon publication at:
http://www.marine.rutgers.edu/globalnews/documents.htm

Beusen, A. H. W., Bouwman, A. F., Dürr, H. H.,  Dekkers, A. L. M. and Hartmann, J. 2009. Global patterns of dissolved silica export to the coastal zone: Results from a spatially explicit global model. Global Biogeochemical Cycles 23: GB0A02, doi:10.1029/2008GB003281

Billen, G. & Garnier, J. 2007. River basin nutrient delivery to the coastal sea: Assessing its potential to sustain new production of non-siliceous algae. Marine Chemistry 106: 148-160 

Mayorga, E., Seitzinger, S.P., Harrison, J.A., Dumont, E., Beusen, A.H.W., Bouwman, A.F., Fekete, B., Kroeze, C. and Van Drecht, G. In review. Global Nutrient Export from WaterSheds 2 (NEWS 2): Model development and implementation. Environmental Modeling & Software

Seitzinger, S. P. et al. In press. Global river nutrient export: A scenario analysis of past and future trends. Global Biogeochemical Cycles, doi:10.1029/2009GB003587

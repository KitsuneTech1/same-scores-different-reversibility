# Third-party data and attribution

This repository redistributes a small set of derived values from public sources: the weekly
one-week-ahead US incident-death median of each forecasting model listed below, and weekly US
incident-death totals derived from the reference data. Raw archive files are not redistributed.

## Forecasts

Source: the US COVID-19 Forecast Hub, https://github.com/reichlab/covid19-forecast-hub, at commit
52f10b79f02af0af7940a0a9a02314a563c04569. Cramer, E. Y., et al. (2022), The United States COVID-19
Forecast Hub dataset, Scientific Data 9, 462. Each model's forecasts remain under the license its
team declared in the Hub, shown here. Where a license requires its notice to travel with copies, the
full text is in papers/paper-1/licenses/.

| Model | Team | License |
|:---|:---|:---|
| BPagano-RtDriven | BPagano | CC-BY-4.0 |
| CEID-Walk | University of Georgia Center for the Ecology of Infectious Diseases Forecasting Working Group | CC-BY-4.0 |
| COVIDhub-baseline | COVID-19 Forecast Hub | CC-BY-4.0 |
| COVIDhub-ensemble | COVID-19 Forecast Hub | CC-BY-4.0 |
| CU-nochange | Columbia University | Apache-2.0 |
| CU-scenario_high | Columbia University | Apache-2.0 |
| CU-scenario_low | Columbia University | Apache-2.0 |
| CU-scenario_mid | Columbia University | Apache-2.0 |
| CU-select | Columbia University | Apache-2.0 |
| Columbia_UNC-SurvCon | Columbia_UNC | Apache-2.0 |
| CovidAnalytics-DELPHI | CovidAnalytics at MIT | Apache-2.0 |
| DDS-NBDS | Discrete Dynamical Systems | MIT |
| GT-DeepCOVID | GT | CC-BY-4.0 |
| IowaStateLW-STEM | Iowa State - Lily Wang's Research Group | CC-BY-4.0 |
| JCB-PRM | John Burant (JCB) | CC-BY-4.0 |
| JHUAPL-Bucky | Johns Hopkins University Applied Physics Lab | MIT |
| JHU_CSSE-DECOM | Johns Hopkins Center for Systems Science and Engineering | CC-BY-4.0 |
| JHU_IDD-CovidSP | Johns Hopkins ID Dynamics COVID-19 Working Group | MIT |
| Karlen-pypm | Karlen Working Group | GPL-3.0 |
| LANL-GrowthRate | Los Alamos National Labs | LANL notice (licenses/LANL-GrowthRate-LICENSE.txt) |
| LNQ-ens1 | LockNQuay | MIT |
| MOBS-GLEAM_COVID | MOBS Lab at Northeastern | CC-BY-4.0 (licenses/MOBS-GLEAM_COVID-LICENSE.txt) |
| OliverWyman-Navigator | Oliver Wyman | MIT-style (licenses/OliverWyman-Navigator-LICENSE.txt) |
| PSI-DRAFT | Predictive Science Inc | MIT |
| RPI_UW-Mob_Collision | RPI and UW | CC-BY-4.0 |
| RobertWalraven-ESG | Robert Walraven | CC-BY-4.0 |
| SteveMcConnell-CovidComplete | Steve McConnell | CC-BY-4.0 |
| UA-EpiCovDA | University of Arizona | CC-BY-4.0 |
| UCLA-SuEIR | UCLA Statistical Machine Learning Lab | CC-BY-4.0 |
| UCM_MESALab-FoGSEIR | University of California Merced MESA Lab | CC-BY-4.0 |
| UCSD_NEU-DeepGLEAM | UCSD_NEU | CC-BY-4.0 |
| UMass-MechBayes | UMass-Amherst | CC-BY-4.0 |
| UMich-RidgeTfReg | The University of Michigan | CC-BY-4.0 |
| UT-Mobility | UT-Austin COVID-19 Consortium | BSD-3-Clause (licenses/UT-Mobility-LICENSE.txt) |

Median values for three partial-coverage models (IHME-CurveFit, Covid19Sim-Simulator,
USACE-ERDC_SEIR) are withheld because their licenses do not clearly permit redistribution. None of
them is in the 34-model cohort and no result uses them.

## Reference data

Weekly totals are sums of the daily US incident-death rows in the Hub truth file
data-truth/truth-Incident Deaths.csv, which the Hub derives from the COVID-19 Data Repository by the
Center for Systems Science and Engineering (CSSE) at Johns Hopkins University,
https://github.com/CSSEGISandData/COVID-19, licensed CC BY 4.0. Dong, E., Du, H., and Gardner, L.
(2020), An interactive web-based dashboard to track COVID-19 in real time, The Lancet Infectious
Diseases 20(5), 533-534.

## Hub code

The Hub's own code is MIT licensed. This repository reuses none of it. The scripts in bin/ and
papers/paper-1/verify/ were written for this study.

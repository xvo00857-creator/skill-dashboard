from cobra.io import load_model
from cobra.flux_analysis import flux_variability_analysis

m = load_model("textbook")
fva = flux_variability_analysis(
    m, reaction_list=["PFK", "FBA", "TPI", "GAPD"],
    fraction_of_optimum=1.0, processes=1
)
print("FVA_subset_ok (fraction=1.0):")
print(fva.round(4).to_string())

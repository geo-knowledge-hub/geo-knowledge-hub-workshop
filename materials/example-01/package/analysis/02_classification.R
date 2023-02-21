#
# Libraries
#
library(sits)
library(sitsdata)

#
# General definitions
#

# DL Model
ltae_model_file <- "data/derived_data/model/ltae_model_trained.rds"

# Computational resources
coresize <- 4  # Number of cores
memsize  <- 4  # RAM used to classify

# Output directory
output_dir <- "data/derived_data/classification_map"

#
# 1. Creating the output directory
#
fs::dir_create(output_dir, recurse = TRUE)

#
# 2. Loading Trained DL model
#
ltae_model <- readRDS(ltae_model_file)

#
# 3. Building data cube (with local data from sitsdata package)
#
data_dir <- system.file("extdata/Rondonia-20LKP/", package = "sitsdata")

ro_cube_20LKP <- sits_cube(
  source     = "MPC",
  collection = "SENTINEL-2-L2A",
  data_dir   = data_dir,
  parse_info = c("X1", "tile", "band", "date")
)

#
# 4. Generating classification probabilities
#
ro_cube_20LKP_probs <- sits_classify(
  data        = ro_cube_20LKP,
  ml_model    = ltae_model,
  output_dir  = output_dir,
  version     = "ltae",
  multicores  = coresize,
  memsize     = memsize
)

#
# 5. Visualizing the probabilities map
#
plot(ro_cube_20LKP_probs, palette = "YlGn")


#
# 6. Generating thematic map
#
defor_map <- sits_label_classification(
  cube       = ro_cube_20LKP_probs,
  multicores = coresize,
  memsize    = memsize,
  output_dir = output_dir,
  version    = "no_smooth"
)

#
# 7. Visualizing the thematic map
#
plot(defor_map)

#
# 8. Exporting classification results
#

# Probabilities
probs_output_file <- fs::path_join(c(output_dir, "ro_cube_20LKP_probs.rds"))
saveRDS(ro_cube_20LKP_probs, probs_output_file)

# Thematic
thematic_output_file <- fs::path_join(c(output_dir, "defor_map.rds"))
saveRDS(defor_map, thematic_output_file)

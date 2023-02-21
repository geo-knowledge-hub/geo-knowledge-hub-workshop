#
# Libraries
#
library(sits)
library(sitsdata)

#
# General definitions
#

# Classification
probabilities_file <- "data/derived_data/classification_map/ro_cube_20LKP_probs.rds"

# DL Model
ltae_model_file <- "data/derived_data/model/ltae_model_trained.rds"

# Computational resources
coresize <- 4  # Number of cores
memsize  <- 4  # RAM used to classify

# Smoothing algorithm configuration
smooth_type        <- "bayes"
smooth_window_size <- 9
smooth_smoothness  <- 20

# Output directory
output_dir <- "data/derived_data/classification_map_smooth"

#
# 1. Creating the output directory
#
fs::dir_create(output_dir, recurse = TRUE)

#
# 2. Loading classification probabilities
#
ro_cube_20LKP_probs <- readRDS(probabilities_file)

#
# 3. Smoothing the classification probabilities
#
cube_smooth_w9_s20 <- sits_smooth(
  cube        = ro_cube_20LKP_probs,
  type        = smooth_type,
  window_size = smooth_window_size,
  smoothness  = smooth_smoothness,
  multicores  = coresize,
  memsize     = memsize,
  version     = "bayes_w9_s20",
  output_dir  = output_dir
)

#
# 5. Visualizing the smoothed probabilities
#
plot(cube_smooth_w9_s20, palette = "YlGn")

#
# 6. Generating thematic map (Smoothed probabilities)
#
defor_map_smooth_w9_20 <- sits_label_classification(
  cube       = cube_smooth_w9_s20,
  multicores = coresize,
  memsize    = memsize,
  output_dir = output_dir,
  version    = "bayes_w9_s20"
)

#
# 7. Visualizing the smoothed thematic map
#
plot(defor_map_smooth_w9_20)

#
# 8. Exporting smoothed results
#

# Probabilities
probs_output_file <- fs::path_join(c(output_dir, "cube_smooth_w9_s20.rds"))
saveRDS(cube_smooth_w9_s20, probs_output_file)

# Thematic
thematic_output_file <- fs::path_join(c(output_dir, "defor_map_smooth_w9_20.rds"))
saveRDS(defor_map_smooth_w9_20, thematic_output_file)

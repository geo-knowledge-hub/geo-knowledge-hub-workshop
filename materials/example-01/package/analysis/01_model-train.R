#
# Libraries
#
library(sits)
library(sitsdata)

#
# General definitions
#

# DL Model
dl_model_learning_rage <- 0.001

# Output directory
output_dir <- "data/derived_data/model"

#
# 1. Creating output directory
#
fs::dir_create(output_dir, recurse = TRUE)


#
# 1. Loading samples (from sitsdata package)
#
data("samples_prodes_4classes")

#
# 2. Visualizing samples
#
sits_labels_summary(samples_prodes_4classes)

#
# 3. Building data cube (with local data from sitsdata package)
#
data_dir <-
  system.file("extdata/Rondonia-20LKP/", package = "sitsdata")

ro_cube_20LKP <- sits_cube(
  source     = "MPC",
  collection = "SENTINEL-2-L2A",
  data_dir   = data_dir,
  parse_info = c("X1", "tile", "band", "date")
)

#
# 4. Visualizing the data cube
#
plot(
  ro_cube_20LKP,
  dates = "2021-07-25",
  red   = "B11",
  green = "B8A",
  blue  = "B02"
)

#
# 5. Training a deep learning model
#

# selecting only the bands available in the cube
samples_3bands <- sits_select(data  = samples_prodes_4classes,
                              bands = sits_bands(ro_cube_20LKP))

# training a model using LightTAE algorithm
ltae_model <- sits_train(samples   = samples_3bands,
                         ml_method = sits_lighttae(opt_hparams = list(lr = dl_model_learning_rage)))

#
# 6. Visualizing the evolution of the model
#
plot(ltae_model)

#
# 7. Exporting the trained model
#
output_file <- fs::path_join(c(output_dir, "ltae_model_trained.rds"))

saveRDS(ltae_model, output_file)

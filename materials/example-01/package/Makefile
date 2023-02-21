.PHONY: train-model classify smooth-classification clean

#
# Utility commands
#
clean:
	rm -rf data/derived_data/*

	> data/derived_data/.gitignore

#
# Classification commands
#
train-model:  ## Train the classification model
	Rscript analysis/01_model-train.R
	
classify:  ## Classify data from the datacube
	Rscript analysis/02_classification.R
	
smooth-classification:  ## Smooth the classification probabilities
	Rscript analysis/03_classification-smooth.R

#
# Documentation function (thanks for https://marmelab.com/blog/2016/02/29/auto-documented-makefile.html)
#
help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

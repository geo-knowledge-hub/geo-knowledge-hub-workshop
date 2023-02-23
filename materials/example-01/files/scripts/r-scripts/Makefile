.PHONY: docker* environment* execution* help

#
# Docker commands
#
docker-build:  ## (Docker) Build the Docker image of the environment.
	docker build -t "geoknowledgehub/sits-environment:1.2.0" .
	
docker-run: docker-build ## (Docker) Run the Docker image.
	docker run -d \
		--name geo-workshop-application \
		--volume ${PWD}:/mnt/package \
		--publish 8787:8787 \
		geoknowledgehub/sits-environment:1.2.0 || echo "Container already running"
		
docker-exec: docker-run  ## (Docker) Run the classification inside the docker container.
	docker exec geo-workshop-application make execution

#
# Environment commands
#
environment-clean:  ## (Environment) Remove generated results.
	rm -rf Rplots.pdf data/*

	> data/.gitkeep

environment-install:  ## (Environment) Install environment dependencies used to execute the experiments.
	Rscript -e "renv::restore()"
	TORCH_HOME=$(R_LIBS_USER) Rscript -e "torch::install_torch()"
	
environment: environment-clean environment-install  ## (Environment) Configure the environment to start the classification.
	@echo "Environment configured" 

#
# Classification commands
#
execution-model:  ## (Classification) Train the classification model.
	Rscript analysis/01_model-train.R
	
execution-classify:  ## (Classification) Generate a classification map using data cubes and Deep Learning.
	Rscript analysis/02_classification.R
	
execution-smooth:  ## (Classification) Smooth the classification map.
	Rscript analysis/03_classification-smooth.R
	
execution: environment execution-model execution-classify execution-smooth  ## (Classification) Execute the complete classification workflow.

#
# Documentation function (thanks for https://marmelab.com/blog/2016/02/29/auto-documented-makefile.html)
#
help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

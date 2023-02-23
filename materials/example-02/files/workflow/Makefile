.PHONY: download* run*

#
# Utility commands
#
download:  ## (Environment) Download the required files.
	@echo "Downloading processing scripts"
	wget \
		--no-check-certificate \
		-O deforestation-classification.zip \
		https://$(GKHUB_API_ADDRESS)/api/records/$(RECORD_SCRIPTS_ID)/files/deforestation-classification.zip/content

	@echo "Extracting files"
	unzip deforestation-classification.zip

	@echo "Organizing directories"
	mv files/scripts/r-scripts deforestation-classification
	rm -rf files deforestation-classification.zip

run: download  ## (Classification) Download the required files and run the classification.
	cd deforestation-classification \
		&& make docker-exec GKHUB_API_ADDRESS=$(GKHUB_API_ADDRESS) RECORD_ID=$(RECORD_ENVIRONMENT_ID)

#
# Documentation function (thanks for https://marmelab.com/blog/2016/02/29/auto-documented-makefile.html)
#
help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

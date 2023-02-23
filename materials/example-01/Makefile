
.PHONY: package*

#
# Package management commands.
#
package-prepare:  ## Prepare the resources to be shared in the GEO Knowledge Hub.
	@echo "Preparing scripts"
	rm -rf files/scripts/deforestation-classification.zip
	zip -r -q files/scripts/deforestation-classification.zip files/scripts/r-scripts

	@echo "Preparing (mini) datacube files"
	rm -rf files/data/datacube/datacube-sentinel2.zip
	zip -r -q files/data/datacube/datacube-sentinel2.zip files/data/datacube/*.tif

package-load:  ## Load package to the GEO Knowledge Hub. To use this target, you must define the following arguments: GKHUB_API_ADDRESS and GKHUB_API_TOKEN.
	geo-package-loader load \
		--verbose \
		--packages-api https://$(GKHUB_API_ADDRESS)/api/packages \
		--records-api  https://$(GKHUB_API_ADDRESS)/api/records \
		--access-token $(GKHUB_API_TOKEN) \
		--knowledge-package-repository ${PWD}

#
# Documentation function (thanks for https://marmelab.com/blog/2016/02/29/auto-documented-makefile.html).
#
help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

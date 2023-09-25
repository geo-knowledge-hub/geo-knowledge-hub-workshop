## Detecting deforestation using data cubes and deep learning

The Knowledge Package "Detecting deforestation using data cubes and deep learning" presents how the sits package can be used to generate deforestation maps, using time series extracted from data cubes and Deep Learning algorithms.

This directory is a [Knowledge Package Repository](https://github.com/geo-knowledge-hub/geo-package-loader#knowledge-package-repository) containing all the files and metadata needed to publish the package on GEO Knowledge Hub. In total, 9 Knowledge Resources are available:

1. `Article`: Article describing the application methodology
2. `Deforestation Map`: Deforestation map generated with the application
3. `Trained ML Model`: Trained ML Model used to generate the LULC Map
4. `Data Cube`: Data Cube used to extract the input time-series data to generate the LULC Map
5. `Processing scripts`: Processing scripts used to handle data, train model and generate the application results
6. `Samples`: Deforestation samples used to train the ML Model
7. `Docs`: Softwate documentation to support the use and customization of the processing scripts
8. `Workflow`: Processing workflow applied to the scripts to generate the results
9. `Environment`: Docker Image of the container used to run the processing workflow

## Publishing the Knowledge Package

To publish this Knowledge Package in the GEO Knowledge Hub, please follow the commands below:

**1. Prepare the files**

You must first prepare the files (e.g., Zip data and scripts) to publish in the GEO Knowledge Hub. You can do this by using the command below:

> This process can take time as it will build and export a docker image.

```sh
make package-prepare

# Output:
#>  Preparing scripts
#>  rm -rf files/scripts/deforestation-classification.zip
#>  zip -r -q files/scripts/deforestation-classification.zip files/scripts/r-scripts
#>  Preparing (mini) datacube files
#>  rm -rf files/data/datacube/datacube-sentinel2.zip
#>  zip -r -q files/data/datacube/datacube-sentinel2.zip files/data/datacube/*.tif
#>  Preparing classification map results
#>  (Omitted)
```

**2. Load the Knowledge Package**

After preparing the Knowledge Package files, you can load them into the GEO Knowledge Hub. To do that, you must have an access token from a Knowledge Provider account. Then, you can use the following command:

```sh
make package-load GKHUB_API_ADDRESS= GKHUB_API_TOKEN=

# Output:
#>  Packages API....................: https://<GEO Knowledge Hub API Address>/api/packages
#>  Records API.....................: https://<GEO Knowledge Hub API Address>/api/records
#>  Personal Access Token...........: <Your access token>
#>  Knowledge Package repository....: example-02
#>  Configuring the client to upload content to the GEO Knowledge Hub
#>  Done!
#>  Creating the package and its resources
#>  Finished!
```

The parameters used in the make target above are:

- `GKHUB_API_ADDRESS`: Address of the GEO Knowledge Hub Rest API (e.g., `gkhub.earthobservations.org`)
- `GKHUB_API_TOKEN`: Rest API `access token` from a [Knowledge Provider account](https://gkhub.earthobservations.org/doc/docs/concepts/concepts-user-roles#knowledge-provider) (e.g., `LdGANqNilmUIRqjAhche`). You can create this token in the [GEO Knowledge Hub user panel](https://gkhub.earthobservations.org/account/settings/applications/). You need to be logged in to do that.

**3. Publish the Knowledge Package**

Now, the Knowledge Package is loaded in the GEO Knowledge Hub. To publish it, you can use the the GEO Knowledge Hub interface.

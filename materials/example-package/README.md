## Example Knowledge Package

This is an example of a Knowledge Package composed of multiple elements. It is used to introduce the concepts of the GEO Knowledge Hub during the workshop.

> This directory is a [Knowledge Package Repository](https://github.com/geo-knowledge-hub/geo-package-loader#knowledge-package-repository) containing all the files and metadata needed to publish the package on GEO Knowledge Hub.

## Publishing the Knowledge Package

To publish this Knowledge Package in the GEO Knowledge Hub, please follow the commands below:

**1. Load the Knowledge Package**

You can load the Knowledge Package into the GEO Knowledge Hub using the following command:

> You must have an access token from a Knowledge Provider account

```sh
make package-load GKHUB_API_ADDRESS= GKHUB_API_TOKEN=

# Output:
#>  Packages API....................: https://<GEO Knowledge Hub API Address>/api/packages
#>  Records API.....................: https://<GEO Knowledge Hub API Address>/api/records
#>  Personal Access Token...........: <Your access token>
#>  Knowledge Package repository....: example-01
#>  Configuring the client to upload content to the GEO Knowledge Hub
#>  Done!
#>  Creating the package and its resources
#>  Finished!
```

The parameters used in the make target above are:

- `GKHUB_API_ADDRESS`: Address of the GEO Knowledge Hub Rest API (e.g., `gkhub.earthobservations.org`)
- `GKHUB_API_TOKEN`: Rest API `access token` from a [Knowledge Provider account](https://gkhub.earthobservations.org/doc/docs/concepts/concepts-user-roles#knowledge-provider) (e.g., `LdGANqNilmUIRqjAhche`). You can create this token in the [GEO Knowledge Hub user panel](https://gkhub.earthobservations.org/account/settings/applications/). You need to be logged in to do that.

**2. Publish the Knowledge Package**

Now, the Knowledge Package is loaded in the GEO Knowledge Hub. To publish it, you can use the the GEO Knowledge Hub interface.

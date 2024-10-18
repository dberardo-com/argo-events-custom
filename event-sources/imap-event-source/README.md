## how to build

docker build -t mycustom_image -f .\Dockerfile src

docker push mycustom_image

## how to use

kubectl apply -f k8s-manifests.yml

# 

# Generate application keys (Critical for Federation) and other tasks
```shell
docker compose exec pixelfed php artisan instance:actor
docker compose exec pixelfed php artisan import:cities
docker compose exec pixelfed php artisan passport:keys
```

# Generate first admin user
```shell
docker compose exec pixelfed php artisan user:create
```

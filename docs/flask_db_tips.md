# Flask DB Tips

## Show Current Migration

```bash
flask --app recap db current
```
## Show History

```bash
flask --app recap db history
```

## Run Migrations

```bash
flask --app recap db migrate
flask --app recap db upgrade
```

## Rollback Migrations

```bash
flask --app recap db downgrade
```

## Create New Migration

```bash
flask --app recap db migrate
```

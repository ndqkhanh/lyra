---
name: api-design
description: RESTful API design patterns and best practices
origin: ECC
tags: [api, rest, design, best-practices]
triggers: [api, rest, endpoint]
---

# API Design

## REST Principles

- **Resources**: Use nouns, not verbs (`/users` not `/getUsers`)
- **HTTP Methods**: GET (read), POST (create), PUT/PATCH (update), DELETE (delete)
- **Status Codes**: 200 (OK), 201 (Created), 400 (Bad Request), 404 (Not Found), 500 (Server Error)
- **Versioning**: `/api/v1/users`

## Response Format

```json
{
  "success": true,
  "data": {...},
  "error": null,
  "meta": {
    "page": 1,
    "total": 100
  }
}
```

## Best Practices

- Use pagination for lists
- Implement rate limiting
- Provide clear error messages
- Use HTTPS only
- Document with OpenAPI/Swagger

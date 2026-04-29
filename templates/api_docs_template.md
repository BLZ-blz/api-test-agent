# {{ spec.info.title }} ({{ spec.info.version }})

{{ spec.info.description if spec.info.description else "No description provided." }}

{% for path, path_item in spec.paths.items() %}
## `{{ path }}`

{% for method, operation in path_item.model_dump().items() %}
{% if operation is mapping %}
### `{{ method | upper }} {{ path }}`

**Summary**: {{ operation.summary if operation.summary else "N/A" }}
**Operation ID**: {{ operation.operationId if operation.operationId else "N/A" }}
**Description**: {{ operation.description if operation.description else "N/A" }}

{% if operation.parameters %}
**Parameters**:
{% for param in operation.parameters %}
- `{{ param.name }}` ({{ param.in_ | capitalize }}): {{ param.description if param.description else "N/A" }} {% if param.required %}(Required){% endif %}
  Type: `{{ param.schema_.type if param.schema_ and param.schema_.type else "N/A" }}`
{% endfor %}
{% endif %}

{% if operation.requestBody %}
**Request Body**: {% if operation.requestBody.required %}(Required){% endif %}
{% for media_type, content in operation.requestBody.content.items() %}
  - `{{ media_type }}`:
    Schema:
    ```json
    {{ content.schema | tojson(indent=2) }}
    ```
{% endfor %}
{% endif %}

**Responses**:
{% for status_code, response in operation.responses.items() %}
- `{{ status_code }}`: {{ response.description }}
{% if response.content %}
  {% for media_type, content in response.content.items() %}
    - `{{ media_type }}`:
      Schema:
      ```json
      {{ content.schema | tojson(indent=2) }}
      ```
  {% endfor %}
{% endif %}
{% endfor %}

{% endif %}
{% endfor %}
{% endfor %}

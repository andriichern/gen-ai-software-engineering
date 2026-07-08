# OpenAPI 3.0.0 Specification

```yaml
openapi: 3.0.0
info:
  title: Intelligent Customer Support Ticket System
  version: 1.0.0
  description: REST API for managing customer support tickets with multi-format import and automatic categorization.

servers:
  - url: http://localhost:8000
    description: Local development server

paths:
  /health:
    get:
      operationId: healthCheck
      summary: Health check endpoint
      tags:
        - Utilities
      responses:
        "200":
          description: Server is healthy
          content:
            application/json:
              schema:
                type: object
                properties:
                  status:
                    type: string
                    example: ok

  /tickets:
    post:
      operationId: createTicket
      summary: Create a new ticket
      tags:
        - Tickets
      parameters:
        - name: auto_classify
          in: query
          schema:
            type: boolean
            default: false
          description: Automatically classify ticket on creation
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: "#/components/schemas/TicketCreate"
      responses:
        "201":
          description: Ticket created successfully
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/Ticket"
        "400":
          description: Validation error
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/ValidationError"

    get:
      operationId: listTickets
      summary: List tickets with optional filters
      tags:
        - Tickets
      parameters:
        - name: category
          in: query
          schema:
            type: string
          description: Filter by category
        - name: priority
          in: query
          schema:
            type: string
            enum: [urgent, high, medium, low]
          description: Filter by priority
        - name: status
          in: query
          schema:
            type: string
            enum: [new, in_progress, waiting_customer, resolved, closed]
          description: Filter by status
        - name: customer_id
          in: query
          schema:
            type: string
          description: Filter by customer ID
        - name: assigned_to
          in: query
          schema:
            type: string
          description: Filter by assigned agent
        - name: tag
          in: query
          schema:
            type: string
          description: Filter by tag
      responses:
        "200":
          description: List of tickets
          content:
            application/json:
              schema:
                type: array
                items:
                  $ref: "#/components/schemas/Ticket"

  /tickets/{ticket_id}:
    get:
      operationId: getTicket
      summary: Get a specific ticket by ID
      tags:
        - Tickets
      parameters:
        - name: ticket_id
          in: path
          required: true
          schema:
            type: string
            format: uuid
      responses:
        "200":
          description: Ticket details
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/Ticket"
        "404":
          description: Ticket not found
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/NotFoundError"

    put:
      operationId: updateTicket
      summary: Update a ticket
      tags:
        - Tickets
      parameters:
        - name: ticket_id
          in: path
          required: true
          schema:
            type: string
            format: uuid
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: "#/components/schemas/TicketUpdate"
      responses:
        "200":
          description: Ticket updated successfully
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/Ticket"
        "400":
          description: Validation error
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/ValidationError"
        "404":
          description: Ticket not found
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/NotFoundError"

    delete:
      operationId: deleteTicket
      summary: Delete a ticket
      tags:
        - Tickets
      parameters:
        - name: ticket_id
          in: path
          required: true
          schema:
            type: string
            format: uuid
      responses:
        "204":
          description: Ticket deleted successfully
        "404":
          description: Ticket not found
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/NotFoundError"

  /tickets/import:
    post:
      operationId: importTickets
      summary: Bulk import tickets from CSV, JSON, or XML file
      tags:
        - Tickets
      parameters:
        - name: auto_classify
          in: query
          schema:
            type: boolean
            default: false
          description: Automatically classify imported tickets
      requestBody:
        required: true
        content:
          multipart/form-data:
            schema:
              type: object
              properties:
                file:
                  type: string
                  format: binary
                  description: CSV, JSON, or XML file (format detected by extension)
      responses:
        "200":
          description: Import summary
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/ImportSummary"
        "400":
          description: Unsupported format or malformed file
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/ImportError"
        "422":
          description: File parsing error
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/ImportError"

  /tickets/{ticket_id}/auto-classify:
    post:
      operationId: autoClassifyTicket
      summary: Trigger auto-classification for a ticket
      tags:
        - Tickets
      parameters:
        - name: ticket_id
          in: path
          required: true
          schema:
            type: string
            format: uuid
      responses:
        "200":
          description: Classification result
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/ClassificationResult"
        "404":
          description: Ticket not found
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/NotFoundError"

  /category/list:
    get:
      operationId: listCategories
      summary: List all categories with their keywords
      tags:
        - Categories
      responses:
        "200":
          description: List of categories
          content:
            application/json:
              schema:
                type: array
                items:
                  $ref: "#/components/schemas/CategoryKeywords"

  /category/{key}:
    get:
      operationId: getCategory
      summary: Get a specific category by key
      tags:
        - Categories
      parameters:
        - name: key
          in: path
          required: true
          schema:
            type: string
      responses:
        "200":
          description: Category details
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/CategoryKeywords"
        "404":
          description: Category not found
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/NotFoundError"

    put:
      operationId: updateCategory
      summary: Add keywords to an existing category
      tags:
        - Categories
      parameters:
        - name: key
          in: path
          required: true
          schema:
            type: string
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: "#/components/schemas/CategoryKeywordsUpdate"
      responses:
        "200":
          description: Updated category
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/CategoryKeywords"
        "404":
          description: Category not found
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/NotFoundError"

  /category:
    post:
      operationId: createCategory
      summary: Create a new category
      tags:
        - Categories
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: "#/components/schemas/CategoryCreate"
      responses:
        "201":
          description: Category created successfully
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/CategoryKeywords"
        "400":
          description: Validation error
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/ValidationError"

components:
  schemas:
    Ticket:
      type: object
      properties:
        id:
          type: string
          format: uuid
        customer_id:
          type: string
        customer_email:
          type: string
          format: email
        customer_name:
          type: string
        subject:
          type: string
          minLength: 1
          maxLength: 200
        description:
          type: string
          minLength: 10
          maxLength: 2000
        category:
          type: string
        priority:
          $ref: "#/components/schemas/Priority"
        status:
          $ref: "#/components/schemas/Status"
        created_at:
          type: string
          format: date-time
        updated_at:
          type: string
          format: date-time
        resolved_at:
          type: string
          format: date-time
          nullable: true
        assigned_to:
          type: string
          nullable: true
        tags:
          type: array
          items:
            type: string
        metadata:
          $ref: "#/components/schemas/TicketMetadata"
        classification_confidence:
          type: number
          format: float
          nullable: true
        classification_overridden:
          type: boolean

    TicketCreate:
      type: object
      required:
        - customer_id
        - customer_email
        - customer_name
        - subject
        - description
      properties:
        customer_id:
          type: string
        customer_email:
          type: string
          format: email
        customer_name:
          type: string
        subject:
          type: string
          minLength: 1
          maxLength: 200
        description:
          type: string
          minLength: 10
          maxLength: 2000
        category:
          type: string
          nullable: true
        priority:
          $ref: "#/components/schemas/Priority"
          nullable: true
        status:
          $ref: "#/components/schemas/Status"
          default: new
        assigned_to:
          type: string
          nullable: true
        tags:
          type: array
          items:
            type: string
        metadata:
          $ref: "#/components/schemas/TicketMetadata"

    TicketUpdate:
      type: object
      properties:
        customer_id:
          type: string
        customer_email:
          type: string
          format: email
        customer_name:
          type: string
        subject:
          type: string
          minLength: 1
          maxLength: 200
        description:
          type: string
          minLength: 10
          maxLength: 2000
        category:
          type: string
        priority:
          $ref: "#/components/schemas/Priority"
        status:
          $ref: "#/components/schemas/Status"
        assigned_to:
          type: string
        tags:
          type: array
          items:
            type: string
        metadata:
          $ref: "#/components/schemas/TicketMetadata"

    TicketMetadata:
      type: object
      properties:
        source:
          $ref: "#/components/schemas/Source"
        browser:
          type: string
          nullable: true
        device_type:
          $ref: "#/components/schemas/DeviceType"
          nullable: true

    Priority:
      type: string
      enum: [urgent, high, medium, low]

    Status:
      type: string
      enum: [new, in_progress, waiting_customer, resolved, closed]

    Source:
      type: string
      enum: [web_form, email, api, chat, phone]

    DeviceType:
      type: string
      enum: [desktop, mobile, tablet]

    ImportSummary:
      type: object
      properties:
        total:
          type: integer
        successful:
          type: integer
        failed:
          type: integer
        errors:
          type: array
          items:
            $ref: "#/components/schemas/ImportRowError"

    ImportRowError:
      type: object
      properties:
        index:
          type: integer
        error:
          type: string

    ClassificationResult:
      type: object
      properties:
        category:
          type: string
        priority:
          $ref: "#/components/schemas/Priority"
        confidence:
          type: number
          format: float
        reasoning:
          type: string
        keywords_found:
          type: array
          items:
            type: string

    CategoryKeywords:
      type: object
      properties:
        category:
          type: string
        keywords:
          type: array
          items:
            type: string

    CategoryCreate:
      type: object
      required:
        - key
      properties:
        key:
          type: string
          pattern: ^[a-z][a-z0-9_]*$
        keywords:
          type: array
          items:
            type: string

    CategoryKeywordsUpdate:
      type: object
      required:
        - keywords
      properties:
        keywords:
          type: array
          items:
            type: string

    ValidationError:
      type: object
      properties:
        detail:
          type: array
          items:
            type: object

    NotFoundError:
      type: object
      properties:
        detail:
          type: string

    ImportError:
      type: object
      properties:
        detail:
          type: string
```

#!/usr/bin/env node

/**
 * FIXME: This should be updated so that no 'any' types are generated
 * And should possibly be written in typescript
 *
 * This script fetches the OpenAPI schema from a running API server and generates
 * TypeScript interfaces that match the API models.
 *
 * Usage:
 * 1. Make sure your API server is running
 * 2. Run this script with: node ./scripts/generate-api-types.js
 */



import fs from 'fs';
import path from 'path';
import https from 'https';
import http from 'http';
import { fileURLToPath } from 'url';

// Configuration
const API_URL = 'http://10.0.0.3:8000/openapi.json';
// Get current file directory in ES modules
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const OUTPUT_FILE = path.resolve(__dirname, '../src/utils/generated-api-types.ts');

async function fetchOpenApiSpec(url) {
    return new Promise((resolve, reject) => {
        const client = url.startsWith('https') ? https : http;

        client.get(url, (res) => {
            let data = '';

            res.on('data', (chunk) => {
                data += chunk;
            });

            res.on('end', () => {
                try {
                    const schema = JSON.parse(data);
                    resolve(schema);
                } catch (err) {
                    reject(new Error(`Failed to parse OpenAPI schema: ${err.message}`));
                }
            });
        }).on('error', (err) => {
            reject(new Error(`Failed to fetch OpenAPI schema: ${err.message}`));
        });
    });
}

function generateTypeFromSchema(schema, modelName) {
    const modelSchema = schema.components.schemas[modelName];
    if (!modelSchema) {
        throw new Error(`Schema not found for model: ${modelName}`);
    }

    let typeDefinition = `export interface ${modelName} {\n`;

    // Process properties
    if (modelSchema.properties) {
        Object.entries(modelSchema.properties).forEach(([propName, propSchema]) => {
            const isRequired = modelSchema.required && modelSchema.required.includes(propName);
            const optional = isRequired ? '' : '?';
            let tsType;

            switch (propSchema.type) {
                case 'string':
                    if (propSchema.format === 'date' || propSchema.format === 'date-time') {
                        tsType = 'string'; // Could also use Date but string is more compatible with API
                    } else if (propSchema.format === 'uuid') {
                        tsType = 'string';
                    } else {
                        tsType = 'string';
                    }
                    break;
                case 'integer':
                case 'number':
                    tsType = 'number';
                    break;
                case 'boolean':
                    tsType = 'boolean';
                    break;
                case 'array':
                    if (propSchema.items.type) {
                        tsType = `${propSchema.items.type}[]`;
                    } else if (propSchema.items.$ref) {
                        const refType = propSchema.items.$ref.split('/').pop();
                        tsType = `${refType}[]`;
                    } else {
                        tsType = 'any[]';
                    }
                    break;
                case 'object':
                    tsType = 'Record<string, any>';
                    break;
                default:
                    if (propSchema.$ref) {
                        tsType = propSchema.$ref.split('/').pop();
                    } else {
                        tsType = 'any';
                    }
            }

            // Add description as comment if available
            if (propSchema.description) {
                typeDefinition += `  /** ${propSchema.description} */\n`;
            }

            typeDefinition += `  ${propName}${optional}: ${tsType};\n`;
        });
    }

    typeDefinition += '}\n\n';
    return typeDefinition;
}

async function generateTypes() {
    try {
        console.log('Fetching OpenAPI schema...');
        const schema = await fetchOpenApiSpec(API_URL);

        console.log('Generating TypeScript interfaces...');
        let output = '/**\n';
        output += ' * GENERATED FILE - DO NOT EDIT\n';
        output += ' * This file was automatically generated from the OpenAPI schema.\n';
        output += ' * Run generate-api-types.js to regenerate.\n';
        output += ' */\n\n';

        // Generate interfaces for each schema
        for (const modelName in schema.components.schemas) {
            output += generateTypeFromSchema(schema, modelName);
        }

        // Add utility functions
        output += `/**
 * API Error Response
 */
export interface ApiError {
  detail: string;
}

/**
 * Type guard to check if a response is an ApiError
 */
export function isApiError(obj: any): obj is ApiError {
  return obj && typeof obj === 'object' && 'detail' in obj;
}

/**
 * Helper to fetch data from the API with proper error handling
 */
export async function fetchApi<T>(
  url: string,
  options?: RequestInit
): Promise<T> {
  const response = await fetch(url, options);

  if (!response.ok) {
    const errorData = await response.json();
    throw new Error(errorData.detail || 'An error occurred');
  }

  return response.json() as Promise<T>;
}
`;

        // Write to file
        fs.writeFileSync(OUTPUT_FILE, output);
        console.log(`TypeScript interfaces generated successfully at ${OUTPUT_FILE}`);
    } catch (error) {
        console.error('Error generating TypeScript interfaces:', error);
        process.exit(1);
    }
}

// Run the generator
generateTypes();
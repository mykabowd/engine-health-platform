{{/*
Base name for chart resources.
*/}}
{{- define "engine-health-platform.name" -}}
engine-health-platform
{{- end -}}

{{/*
Fully-qualified name for a given component ("api" or "web"), prefixed by the
release name so multiple releases can coexist in the same namespace.
*/}}
{{- define "engine-health-platform.componentName" -}}
{{- $releaseName := index . 0 -}}
{{- $component := index . 1 -}}
{{- printf "%s-%s" $releaseName $component -}}
{{- end -}}

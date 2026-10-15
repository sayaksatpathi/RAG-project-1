{{- define "ragbench.name" -}}
{{- .Chart.Name -}}
{{- end -}}

{{- define "ragbench.fullname" -}}
{{- printf "%s-%s" .Release.Name .Chart.Name | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "ragbench.labels" -}}
app.kubernetes.io/name: {{ include "ragbench.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version }}
{{- end -}}

{{- define "ragbench.selectorLabels" -}}
app.kubernetes.io/name: {{ include "ragbench.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{- define "ragbench.secretName" -}}
{{- if .Values.existingSecret -}}
{{- .Values.existingSecret -}}
{{- else -}}
{{- printf "%s-secret" (include "ragbench.fullname" .) -}}
{{- end -}}
{{- end -}}

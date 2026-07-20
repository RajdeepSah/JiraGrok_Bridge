import { useQuery } from '@tanstack/react-query';

import { getTemplate, getTemplates } from '../../api/endpoints';

export function useTemplates() {
  return useQuery({ queryKey: ['templates'], queryFn: getTemplates });
}

export function useTemplateDetail(id: string | null) {
  return useQuery({
    queryKey: ['template', id],
    queryFn: () => getTemplate(id as string),
    enabled: id != null,
  });
}

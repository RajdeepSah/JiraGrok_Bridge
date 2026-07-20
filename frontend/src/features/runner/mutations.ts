import { useMutation } from '@tanstack/react-query';

import { postComment, runIssue } from '../../api/endpoints';
import type { CommentRequestBody, Credentials, RunRequestBody } from '../../api/types';

export function useRun() {
  return useMutation({
    mutationFn: (vars: { body: RunRequestBody; creds: Credentials }) => runIssue(vars.body, vars.creds),
  });
}

export function usePostComment() {
  return useMutation({
    mutationFn: (vars: { body: CommentRequestBody; creds: Credentials }) =>
      postComment(vars.body, vars.creds),
  });
}

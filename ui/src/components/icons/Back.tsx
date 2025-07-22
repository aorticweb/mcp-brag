/*
 * Copyright 2025 Block, Inc.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

export default function Back({ className = '' }) {
  return (
    <svg
      width="1.5rem"
      height="1.5rem"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      aria-hidden="true"
      className={className}
    >
      <path
        fillRule="evenodd"
        clipRule="evenodd"
        d="M.5 12c0-.413.17-.807.47-1.09l9-8.5a1.5 1.5 0 1 1 2.06 2.18L5.773 10.5H21.5a1.5 1.5 0 1 1 0 3H5.773l6.257 5.91a1.5 1.5 0 1 1-2.06 2.18l-9-8.5A1.5 1.5 0 0 1 .5 12Z"
        fill="currentColor"
      ></path>
    </svg>
  );
}

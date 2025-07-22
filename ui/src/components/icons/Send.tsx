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

export default function Send({ className = '' }) {
  return (
    <svg
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      aria-hidden="true"
      className={className}
    >
      <path
        fillRule="evenodd"
        clipRule="evenodd"
        d="M20.707 3.293a1 1 0 0 1 .25.994l-5.4 18a1 1 0 0 1-1.886.084l-3.44-8.602-8.602-3.44a1 1 0 0 1 .084-1.887l18-5.4a1 1 0 0 1 .994.25Zm-8.534 9.948 2.292 5.729L18.509 5.49 5.03 9.535l5.73 2.292 1.333-1.334a1 1 0 0 1 1.414 1.414l-1.334 1.334Z"
        fill="currentColor"
      ></path>
    </svg>
  );
}

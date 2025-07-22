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

export default function Edit({ className = '' }) {
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
        d="M16.287 3.292a1 1 0 0 1 1.41-.001l3.008 2.988a1 1 0 0 1 .002 1.416l-2.618 2.62-.001.002-7.552 7.584c-.55.552-1.23.955-1.977 1.175l-3.714 1.363a1 1 0 0 1-1.286-1.276l1.338-3.74a4.606 4.606 0 0 1 1.17-1.962l7.595-7.554 2.625-2.615Zm-1.92 4.734-6.89 6.853a2.607 2.607 0 0 0-.667 1.128l-.02.061-.628 1.757 1.741-.64a.985.985 0 0 1 .071-.022 2.633 2.633 0 0 0 1.145-.674l6.847-6.876-1.598-1.587Zm3.01.171 1.207-1.206-1.59-1.58-1.209 1.204 1.593 1.582Z"
        fill="currentColor"
      ></path>
    </svg>
  );
}
